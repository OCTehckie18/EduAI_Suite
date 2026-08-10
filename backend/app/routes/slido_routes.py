from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from app.models.slido import (
    PresentationAssignment, PresentationSubmission, SlidoSession,
    SlidoPoll, PollResponse, SlidoQnA, QnAUpvote, SubmissionInteraction
)
from app.models.user import User
from app.schemas.slido import (
    PresentationAssignmentCreate, PresentationAssignmentUpdate, PresentationAssignmentResponse,
    PresentationSubmissionCreate, PresentationSubmissionGrade, PresentationSubmissionResponse,
    SlidoSessionCreate, SlidoSessionUpdate, SlidoSessionResponse,
    SlidoPollCreate, SlidoPollResponse,
    PollResponseCreate, PollResponseResponse,
    SlidoQnACreate, SlidoQnAUpdate, SlidoQnAResponse,
    QnAUpvoteResponse,
    SubmissionInteractionCreate, SubmissionInteractionUpdate, SubmissionInteractionResponse
)
from app.services.storage_service import get_storage_service
from datetime import datetime
from typing import Optional, List
import secrets
import mimetypes

slido_router = APIRouter(prefix="/slido", tags=["Slido"])


def validate_pptx_file(file_content: bytes, filename: str) -> bool:
    """
    Validate PPTX file signature and extension.
    PPTX files are ZIP archives with specific internal structure.
    """
    if not filename.lower().endswith('.pptx'):
        return False
    if not file_content.startswith(b'PK\x03\x04'):
        return False

    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type and mime_type != 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
        if mime_type != 'application/zip':
            return False

    return True


def save_pptx_file(file_content: bytes, file_name: str) -> Optional[str]:
    """Save PPTX file to Supabase Storage and return a signed URL."""
    try:
        storage = get_storage_service()
        unique_filename = f"{secrets.token_hex(16)}_{file_name}"
        object_key = storage.upload_file(
            file_content=file_content,
            file_name=unique_filename,
            folder='presentations',
            content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
        if not object_key:
            return None

        presigned_url = storage.generate_presigned_url(
            object_key=object_key,
            expiration=7 * 24 * 3600  # 7 days
        )

        return presigned_url
    except Exception as e:
        print(f"Error saving PPTX file: {e}")
        return None


# ==================== PresentationAssignment Endpoints ====================

@slido_router.post("/assignments", response_model=PresentationAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    assignment: PresentationAssignmentCreate,
    teacher_id: int = Query(...)
):
    """Create a new presentation assignment"""
    try:
        new_assignment = PresentationAssignment(
            teacher_id=teacher_id,
            course_id=assignment.course_id,
            title=assignment.title,
            description=assignment.description,
            deadline=assignment.deadline
        )
        await new_assignment.assign_id()
        await new_assignment.insert()
        res = new_assignment.model_dump()
        res["id"] = new_assignment.int_id
        return res
    except Exception as e:
        print(f"Error creating assignment: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create assignment: {str(e)}")


@slido_router.get("/assignments/{assignment_id}", response_model=PresentationAssignmentResponse)
async def get_assignment(assignment_id: int):
    """Get a specific assignment"""
    assignment = await PresentationAssignment.find_one(PresentationAssignment.int_id == assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    res = assignment.model_dump()
    res["id"] = assignment.int_id
    return res


@slido_router.get("/assignments", response_model=List[PresentationAssignmentResponse])
async def list_assignments(
    teacher_id: Optional[int] = Query(None),
    course_id: Optional[int] = Query(None)
):
    """List assignments, optionally filtered by teacher or course"""
    query = PresentationAssignment.find_all()
    if teacher_id:
        query = query.find(PresentationAssignment.teacher_id == teacher_id)
    if course_id:
        query = query.find(PresentationAssignment.course_id == course_id)
        
    assignments = await query.to_list()
    res = []
    for a in assignments:
        d = a.model_dump()
        d["id"] = a.int_id
        res.append(d)
    return res


@slido_router.put("/assignments/{assignment_id}", response_model=PresentationAssignmentResponse)
async def update_assignment(
    assignment_id: int,
    update_data: PresentationAssignmentUpdate
):
    """Update an assignment"""
    assignment = await PresentationAssignment.find_one(PresentationAssignment.int_id == assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(assignment, key, value)

    assignment.updated_at = datetime.utcnow()
    await assignment.save()
    
    res = assignment.model_dump()
    res["id"] = assignment.int_id
    return res


# ==================== PresentationSubmission Endpoints ====================

@slido_router.post("/submissions/upload", response_model=PresentationSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def upload_presentation(
    assignment_id: int = Form(...),
    student_id: int = Form(...),
    file: UploadFile = File(...)
):
    """Upload a presentation file for an assignment"""
    # Verify assignment exists
    assignment = await PresentationAssignment.find_one(PresentationAssignment.int_id == assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Verify student exists
    student = await User.find_one(User.int_id == student_id)
    if not student:
        raise HTTPException(status_code=403, detail="Student not found")

    # Read and validate file
    file_content = await file.read()
    if not validate_pptx_file(file_content, file.filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid file. Only .pptx files are accepted."
        )

    # Check file size (max 100MB)
    if len(file_content) > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=400, detail="File too large. Max 100MB.")

    # Save file to Supabase Storage
    file_url = save_pptx_file(file_content, file.filename)
    if not file_url:
        raise HTTPException(
            status_code=500,
            detail="Failed to save file. Please try again."
        )

    # Check if late
    is_late = False
    if assignment.deadline and datetime.utcnow() > assignment.deadline:
        is_late = True

    # Check for existing submission and update or create
    existing = await PresentationSubmission.find_one(
        PresentationSubmission.assignment_id == assignment_id,
        PresentationSubmission.student_id == student_id
    )

    if existing:
        existing.file_url = file_url
        existing.file_name = file.filename
        existing.submitted_at = datetime.utcnow()
        existing.is_late = is_late
        await existing.save()
        res = existing.model_dump()
        res["id"] = existing.int_id
        return res

    submission = PresentationSubmission(
        assignment_id=assignment_id,
        student_id=student_id,
        file_url=file_url,
        file_name=file.filename,
        is_late=is_late,
        status="draft"
    )
    await submission.assign_id()
    await submission.insert()
    
    res = submission.model_dump()
    res["id"] = submission.int_id
    return res


@slido_router.get("/submissions/{submission_id}", response_model=PresentationSubmissionResponse)
async def get_submission(submission_id: int):
    """Get a submission"""
    submission = await PresentationSubmission.find_one(PresentationSubmission.int_id == submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    res = submission.model_dump()
    res["id"] = submission.int_id
    return res


@slido_router.get("/submissions", response_model=List[PresentationSubmissionResponse])
async def list_submissions(
    assignment_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None)
):
    """List submissions, optionally filtered"""
    query = PresentationSubmission.find_all()
    if assignment_id:
        query = query.find(PresentationSubmission.assignment_id == assignment_id)
    if student_id:
        query = query.find(PresentationSubmission.student_id == student_id)
        
    subs = await query.to_list()
    res = []
    for s in subs:
        d = s.model_dump()
        d["id"] = s.int_id
        res.append(d)
    return res


@slido_router.post("/submissions/{submission_id}/grade", response_model=PresentationSubmissionResponse)
async def grade_submission(
    submission_id: int,
    grade_data: PresentationSubmissionGrade,
    teacher_id: int = Query(...)
):
    """Grade a submission"""
    submission = await PresentationSubmission.find_one(PresentationSubmission.int_id == submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Verify teacher owns the assignment
    assignment = await PresentationAssignment.find_one(PresentationAssignment.int_id == submission.assignment_id)
    if not assignment or assignment.teacher_id != teacher_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to grade this submission")

    submission.grade = grade_data.grade
    submission.teacher_feedback = grade_data.teacher_feedback
    submission.graded_at = datetime.utcnow()
    await submission.save()
    
    res = submission.model_dump()
    res["id"] = submission.int_id
    return res


# ==================== SlidoSession Endpoints ====================

async def generate_session_pin() -> str:
    """Generate a unique 6-digit PIN"""
    return ''.join([str(i) for i in secrets.token_bytes(3)]).zfill(6)[:6]


@slido_router.post("/sessions", response_model=SlidoSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SlidoSessionCreate,
    teacher_id: int = Query(...)
):
    """Start a new Slido session"""
    user = await User.find_one(User.int_id == teacher_id)
    if not user:
        raise HTTPException(
            status_code=403, detail="User not found")

    if session_data.assignment_id:
        assignment = await PresentationAssignment.find_one(PresentationAssignment.int_id == session_data.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

    if session_data.submission_id:
        submission = await PresentationSubmission.find_one(PresentationSubmission.int_id == session_data.submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

    pin = await generate_session_pin()
    while await SlidoSession.find_one(SlidoSession.pin == pin):
        pin = await generate_session_pin()

    new_session = SlidoSession(
        teacher_id=teacher_id,
        assignment_id=session_data.assignment_id,
        submission_id=session_data.submission_id,
        pin=pin
    )
    await new_session.assign_id()
    await new_session.insert()
    
    res = new_session.model_dump()
    res["id"] = new_session.int_id
    return res


@slido_router.get("/sessions/{session_id}", response_model=SlidoSessionResponse)
async def get_session(session_id: int):
    """Get a session"""
    session = await SlidoSession.find_one(SlidoSession.int_id == session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    res = session.model_dump()
    res["id"] = session.int_id
    return res


@slido_router.get("/sessions/pin/{pin}", response_model=SlidoSessionResponse)
async def get_session_by_pin(pin: str):
    """Get a session by PIN (for students joining)"""
    session = await SlidoSession.find_one(SlidoSession.pin == pin)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    res = session.model_dump()
    res["id"] = session.int_id
    return res


@slido_router.put("/sessions/{session_id}", response_model=SlidoSessionResponse)
async def update_session(
    session_id: int,
    update_data: SlidoSessionUpdate
):
    """Update session state"""
    session = await SlidoSession.find_one(SlidoSession.int_id == session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(session, key, value)

    session.updated_at = datetime.utcnow()
    await session.save()
    
    res = session.model_dump()
    res["id"] = session.int_id
    return res


@slido_router.post("/sessions/{session_id}/end", response_model=SlidoSessionResponse)
async def end_session(session_id: int):
    """End a session"""
    session = await SlidoSession.find_one(SlidoSession.int_id == session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "ended"
    session.ended_at = datetime.utcnow()
    await session.save()
    
    res = session.model_dump()
    res["id"] = session.int_id
    return res


# ==================== SlidoPoll Endpoints ====================

@slido_router.post("/sessions/{session_id}/polls", response_model=SlidoPollResponse, status_code=status.HTTP_201_CREATED)
async def create_poll(
    session_id: int,
    poll_data: SlidoPollCreate,
    teacher_id: int = Query(...)
):
    """Create a new poll in a session"""
    session = await SlidoSession.find_one(SlidoSession.int_id == session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.teacher_id != teacher_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to create polls in this session")

    poll = SlidoPoll(
        session_id=session_id,
        teacher_id=teacher_id,
        question=poll_data.question,
        poll_type=poll_data.poll_type
    )
    await poll.assign_id()
    await poll.insert()
    
    res = poll.model_dump()
    res["id"] = poll.int_id
    return res


@slido_router.get("/polls/{poll_id}", response_model=SlidoPollResponse)
async def get_poll(poll_id: int):
    """Get a poll"""
    poll = await SlidoPoll.find_one(SlidoPoll.int_id == poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
        
    res = poll.model_dump()
    res["id"] = poll.int_id
    return res


@slido_router.put("/polls/{poll_id}", response_model=SlidoPollResponse)
async def update_poll(
    poll_id: int,
    is_active: bool = Form(...)
):
    """Update poll status"""
    poll = await SlidoPoll.find_one(SlidoPoll.int_id == poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    poll.is_active = is_active
    poll.updated_at = datetime.utcnow()
    await poll.save()
    
    res = poll.model_dump()
    res["id"] = poll.int_id
    return res


@slido_router.post("/polls/{poll_id}/response", response_model=PollResponseResponse, status_code=status.HTTP_201_CREATED)
async def submit_poll_response(
    poll_id: int,
    response: PollResponseCreate,
    student_id: int = Query(...)
):
    """Submit a response to a poll"""
    poll = await SlidoPoll.find_one(SlidoPoll.int_id == poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    poll_response = PollResponse(
        poll_id=poll_id,
        student_id=student_id,
        option_text=response.option_text,
        response_text=response.response_text,
        response_value=response.response_value
    )
    await poll_response.assign_id()
    await poll_response.insert()
    
    poll.total_responses += 1
    await poll.save()
    
    res = poll_response.model_dump()
    res["id"] = poll_response.int_id
    return res


# ==================== SlidoQnA Endpoints ====================

@slido_router.post("/sessions/{session_id}/qna", response_model=SlidoQnAResponse, status_code=status.HTTP_201_CREATED)
async def ask_question(
    session_id: int,
    question_data: SlidoQnACreate,
    student_id: int = Query(...)
):
    """Post a Q&A question"""
    session = await SlidoSession.find_one(SlidoSession.int_id == session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    question = SlidoQnA(
        session_id=session_id,
        student_id=student_id,
        question_text=question_data.question_text,
        is_anonymous=question_data.is_anonymous
    )
    await question.assign_id()
    await question.insert()
    
    res = question.model_dump()
    res["id"] = question.int_id
    return res


@slido_router.get("/qna/{question_id}", response_model=SlidoQnAResponse)
async def get_question(question_id: int):
    """Get a Q&A question"""
    question = await SlidoQnA.find_one(SlidoQnA.int_id == question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    res = question.model_dump()
    res["id"] = question.int_id
    return res


@slido_router.get("/sessions/{session_id}/qna", response_model=List[SlidoQnAResponse])
async def get_session_questions(session_id: int):
    """Get all Q&A questions in a session"""
    questions = await SlidoQnA.find(SlidoQnA.session_id == session_id).sort("-upvotes").to_list()
    res = []
    for q in questions:
        d = q.model_dump()
        d["id"] = q.int_id
        res.append(d)
    return res


@slido_router.post("/qna/{question_id}/upvote", response_model=SlidoQnAResponse)
async def upvote_question(
    question_id: int,
    student_id: int = Query(...)
):
    """Upvote a Q&A question"""
    question = await SlidoQnA.find_one(SlidoQnA.int_id == question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    existing = await QnAUpvote.find_one(
        QnAUpvote.question_id == question_id,
        QnAUpvote.student_id == student_id
    )

    if existing:
        raise HTTPException(
            status_code=400, detail="Already upvoted this question")

    upvote = QnAUpvote(question_id=question_id, student_id=student_id)
    await upvote.assign_id()
    await upvote.insert()
    
    question.upvotes += 1
    question.updated_at = datetime.utcnow()
    await question.save()
    
    res = question.model_dump()
    res["id"] = question.int_id
    return res


@slido_router.post("/qna/{question_id}/answer", response_model=SlidoQnAResponse)
async def answer_question(
    question_id: int,
    update_data: SlidoQnAUpdate,
    teacher_id: int = Query(...)
):
    """Answer a Q&A question (teacher only)"""
    question = await SlidoQnA.find_one(SlidoQnA.int_id == question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    session = await SlidoSession.find_one(SlidoSession.int_id == question.session_id)
    if not session or session.teacher_id != teacher_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to answer questions in this session")

    question.is_answered = update_data.is_answered
    question.teacher_answer = update_data.teacher_answer
    question.answered_at = datetime.utcnow() if update_data.is_answered else None
    question.updated_at = datetime.utcnow()
    await question.save()
    
    res = question.model_dump()
    res["id"] = question.int_id
    return res


# ==================== SubmissionInteraction Endpoints ====================

@slido_router.get("/submissions/{submission_id}/interactions", response_model=List[SubmissionInteractionResponse])
async def list_interactions(submission_id: int):
    """Get all interactions for a submission, ordered by slide_number then order_index"""
    submission = await PresentationSubmission.find_one(PresentationSubmission.int_id == submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    interactions = await SubmissionInteraction.find(
        SubmissionInteraction.submission_id == submission_id
    ).sort("slide_number", "order_index").to_list()
    
    res = []
    for i in interactions:
        d = i.model_dump()
        d["id"] = i.int_id
        res.append(d)
    return res


@slido_router.post("/submissions/{submission_id}/interactions", response_model=SubmissionInteractionResponse, status_code=status.HTTP_201_CREATED)
async def create_interaction(
    submission_id: int,
    interaction_data: SubmissionInteractionCreate
):
    """Add an interaction to a submission (only while in draft status)"""
    submission = await PresentationSubmission.find_one(PresentationSubmission.int_id == submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Cannot add interactions to a finalized submission"
        )

    valid_types = ["poll_multiple_choice", "poll_open_text", "poll_word_cloud", "poll_rating", "qna_prompt"]
    if interaction_data.interaction_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interaction type. Must be one of: {', '.join(valid_types)}"
        )

    interaction = SubmissionInteraction(
        submission_id=submission_id,
        slide_number=interaction_data.slide_number,
        interaction_type=interaction_data.interaction_type,
        config=interaction_data.config,
        order_index=interaction_data.order_index
    )
    await interaction.assign_id()
    await interaction.insert()
    
    res = interaction.model_dump()
    res["id"] = interaction.int_id
    return res


@slido_router.put("/submissions/interactions/{interaction_id}", response_model=SubmissionInteractionResponse)
async def update_interaction(
    interaction_id: int,
    update_data: SubmissionInteractionUpdate
):
    """Update an existing interaction"""
    interaction = await SubmissionInteraction.find_one(SubmissionInteraction.int_id == interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    submission = await PresentationSubmission.find_one(PresentationSubmission.int_id == interaction.submission_id)
    if not submission or submission.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Cannot modify interactions on a finalized submission"
        )

    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(interaction, key, value)

    interaction.updated_at = datetime.utcnow()
    await interaction.save()
    
    res = interaction.model_dump()
    res["id"] = interaction.int_id
    return res


@slido_router.delete("/submissions/interactions/{interaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interaction(interaction_id: int):
    """Remove an interaction from a submission"""
    interaction = await SubmissionInteraction.find_one(SubmissionInteraction.int_id == interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    submission = await PresentationSubmission.find_one(PresentationSubmission.int_id == interaction.submission_id)
    if not submission or submission.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete interactions from a finalized submission"
        )

    await interaction.delete()
    return None


@slido_router.put("/submissions/{submission_id}/submit", response_model=PresentationSubmissionResponse)
async def finalize_submission(submission_id: int):
    """Finalize a draft submission (changes status from 'draft' to 'submitted')"""
    submission = await PresentationSubmission.find_one(PresentationSubmission.int_id == submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Submission is already in '{submission.status}' state"
        )

    submission.status = "submitted"
    submission.submitted_at = datetime.utcnow()
    submission.updated_at = datetime.utcnow()
    await submission.save()
    
    res = submission.model_dump()
    res["id"] = submission.int_id
    return res
