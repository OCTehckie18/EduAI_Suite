from fastapi import APIRouter, HTTPException, Query, File, UploadFile
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.user import User
from app.schemas.lesson import (
    LessonCreateRequest,
    LessonUpdateRequest,
    LessonPostRequest,
    LessonResponse,
    LessonListResponse,
    LessonGenerateRequest
)
from app.services.groq_service import GroqService
from app.utils.plan_parser import CoursePlanParser
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

lesson_router = APIRouter(prefix="/lessons", tags=["Lessons"])


async def resolve_course_id(requested_course_id: int) -> int:
    course = await Course.find_one(Course.int_id == requested_course_id)
    if course:
        return course.int_id

    fallback_course = await Course.find_all().sort("int_id").first_or_none()
    if fallback_course:
        logger.warning(
            "Requested course_id %s not found; falling back to course_id %s",
            requested_course_id,
            fallback_course.int_id,
        )
        return fallback_course.int_id

    raise HTTPException(status_code=400, detail="No courses available to attach lesson")


async def resolve_creator_id() -> int:
    teacher = await User.find(User.role == "teacher").sort("int_id").first_or_none()
    if teacher:
        return teacher.int_id

    existing_user = await User.find_all().sort("int_id").first_or_none()
    if existing_user:
        return existing_user.int_id

    raise HTTPException(status_code=400, detail="A teacher account is required before creating a lesson")


@lesson_router.post("/generate", response_model=dict)
def generate_lesson(request: LessonGenerateRequest):
    """Generate a lesson plan using Groq AI based on topic and optional syllabus context."""
    try:
        result = GroqService.generate_lesson_plan(
            topic=request.topic,
            syllabus_context=request.syllabus_context
        )
        return result
    except Exception as e:
        logger.error(f"Error generating lesson: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@lesson_router.post("/parse-plan")
async def parse_course_plan(file: UploadFile = File(...)):
    """Extract topic and syllabus from an uploaded course plan file using Regex."""
    try:
        content = await file.read()
        filename = file.filename.lower() if file.filename else "unknown.txt"
        
        text = ""
        if filename.endswith(".pdf"):
            text = CoursePlanParser.extract_text_from_pdf(content)
        elif filename.endswith(".docx"):
            text = CoursePlanParser.extract_text_from_docx(content)
        elif filename.endswith(".txt") or filename.endswith(".md"):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1")
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file format. Please upload PDF, DOCX, TXT, or MD."
            )
            
        if not text.strip():
            raise HTTPException(status_code=400, detail="The file appears to be empty or unreadable.")
            
        result = CoursePlanParser.parse_content(text)
        
        # Log parsing results for debugging
        logger.info(f"Parsed plan: Topic='{result['topic']}', SyllabusLength={len(result['syllabus_context'])}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing course plan: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error during parsing: {str(e)}")


@lesson_router.post("", response_model=LessonResponse)
async def create_lesson(request: LessonCreateRequest):
    """Create a new lesson (draft)."""
    try:
        resolved_course_id = await resolve_course_id(request.course_id)
        creator_id = await resolve_creator_id()

        lesson = Lesson(
            course_id=resolved_course_id,
            title=request.title,
            topic=request.topic,
            syllabus_context=request.syllabus_context,
            lecture_flow=request.lecture_flow,
            examples=request.examples,
            activities=request.activities,
            quiz_questions=request.quiz_questions,
            created_by=creator_id,
            posted_at=None
        )
        await lesson.assign_id()
        await lesson.insert()
        return LessonResponse(**{**lesson.model_dump(), "id": lesson.int_id})
    except Exception as e:
        logger.error(f"Error creating lesson: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@lesson_router.get("", response_model=list[LessonListResponse])
async def get_lessons(
    course_id: int = Query(None),
    posted_only: bool = Query(False)
):
    """Get lessons, optionally filtered by course and posted status."""
    try:
        query = Lesson.find_all()

        if course_id:
            query = query.find(Lesson.course_id == course_id)

        if posted_only:
            query = query.find({"posted_at": {"$ne": None}})

        lessons = await query.sort("-created_at").to_list()
        return [LessonListResponse(**{**l.model_dump(), "id": l.int_id}) for l in lessons]
    except Exception as e:
        logger.error(f"Error fetching lessons: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@lesson_router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(lesson_id: int):
    """Get a specific lesson by ID."""
    try:
        lesson = await Lesson.find_one(Lesson.int_id == lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        return LessonResponse(**{**lesson.model_dump(), "id": lesson.int_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lesson: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@lesson_router.put("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    request: LessonUpdateRequest
):
    """Update an existing lesson."""
    try:
        lesson = await Lesson.find_one(Lesson.int_id == lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        # Only update posted_at if lesson hasn't been posted
        if lesson.posted_at:
            raise HTTPException(
                status_code=400, detail="Cannot update a posted lesson")

        # Update fields
        if request.title is not None:
            lesson.title = request.title
        if request.topic is not None:
            lesson.topic = request.topic
        if request.syllabus_context is not None:
            lesson.syllabus_context = request.syllabus_context
        if request.lecture_flow is not None:
            lesson.lecture_flow = request.lecture_flow
        if request.examples is not None:
            lesson.examples = request.examples
        if request.activities is not None:
            lesson.activities = request.activities
        if request.quiz_questions is not None:
            lesson.quiz_questions = request.quiz_questions

        lesson.updated_at = datetime.utcnow()
        await lesson.save()
        return LessonResponse(**{**lesson.model_dump(), "id": lesson.int_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lesson: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@lesson_router.post("/{lesson_id}/post", response_model=LessonResponse)
async def post_lesson(
    lesson_id: int,
    request: LessonPostRequest
):
    """Post a lesson to students (publish)."""
    try:
        lesson = await Lesson.find_one(Lesson.int_id == lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        if lesson.posted_at:
            raise HTTPException(
                status_code=400, detail="Lesson already posted")

        lesson.posted_at = datetime.utcnow()
        await lesson.save()
        logger.info(f"Lesson {lesson_id} posted to course {lesson.course_id}")
        return LessonResponse(**{**lesson.model_dump(), "id": lesson.int_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error posting lesson: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@lesson_router.delete("/{lesson_id}")
async def delete_lesson(lesson_id: int):
    """Delete a lesson."""
    try:
        lesson = await Lesson.find_one(Lesson.int_id == lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        if lesson.posted_at:
            raise HTTPException(
                status_code=400, detail="Cannot delete a posted lesson")

        await lesson.delete()
        logger.info(f"Lesson {lesson_id} deleted")
        return {"message": "Lesson deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lesson: {e}")
        raise HTTPException(status_code=500, detail=str(e))
