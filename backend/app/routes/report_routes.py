from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse
from app.models.report import Report
from app.models.student import Student
from app.models.course import Course
from app.models.submission import Submission
from app.models.exam import ExamAttempt, Exam
from app.models.assignment import Assignment
from app.models.user import User
from app.services.groq_service import GroqService, DEFAULT_MODEL
from app.services.report_template_service import ReportTemplateService
from app.utils.email_utils import send_email
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import uuid
import datetime
import os
import json

report_router = APIRouter(prefix="/reports", tags=["Reports"])

class GenerateReportRequest(BaseModel):
    type: str # 'Class Report', 'Student Report', 'Analytics Export'
    target_id: Optional[int] = None # course_id or student_id depending on type

class SendReportRequest(BaseModel):
    email: str

class ReportResponse(BaseModel):
    id: str
    name: str
    type: str
    date: str
    status: str
    content: Optional[str]

@report_router.get("", response_model=List[ReportResponse])
async def get_reports():
    reports = await Report.find_all().sort("-generated_at").to_list()
    result = []
    for r in reports:
        result.append({
            "id": r.report_id,
            "name": r.name,
            "type": r.type,
            "date": r.generated_at.strftime("%b %d, %Y"),
            "status": r.status,
            "content": r.content
        })
    return result

async def generate_report_background(report_db_id: int, type: str, target_id: int):
    report = await Report.find_one(Report.int_id == report_db_id)
    if not report:
        return
    
    try:
        if type == 'Student Report':
            student = await Student.find_one(Student.int_id == target_id)
            if not student:
                report.status = "failed"
                report.content = "Student not found"
                await report.save()
                return

            # Find the corresponding User for this student to get their exam attempts
            user = await User.find_one(User.email == student.email)
            user_id = user.int_id if user else -1
            
            # Get grades and performance data
            submissions = await Submission.find(Submission.student_name == student.name).to_list()
            exams_with_attempts = await Exam.find({"attempts.student_id": user_id}).to_list()
            
            sub_details = []
            sub_scores = []
            for s in submissions:
                assignment = await Assignment.find_one(Assignment.int_id == s.assignment_id)
                title = assignment.title if assignment else "Unknown Assignment"
                max_score = assignment.max_points if assignment and getattr(assignment, 'max_points', None) else 100
                if s.grade is not None:
                    score_pct = (s.grade / max_score * 100) if max_score > 0 else 0
                    sub_details.append(f"- {title}: {score_pct:.1f}%")
                    sub_scores.append(score_pct)

            exam_details = []
            exam_scores = []
            for exam in exams_with_attempts:
                max_score = sum(q.points for q in exam.questions) if exam.questions else 100
                for a in exam.attempts:
                    if a.student_id == user_id and a.score is not None:
                        score_pct = (a.score / max_score * 100) if max_score > 0 else 0
                        title = exam.title or "Unknown Exam"
                        exam_details.append(f"- {title}: {score_pct:.1f}%")
                        exam_scores.append(score_pct)
            
            avg_sub = sum(sub_scores)/len(sub_scores) if sub_scores else 0
            avg_exam = sum(exam_scores)/len(exam_scores) if exam_scores else 0
            
            prompt = f"""
            Generate a COMPREHENSIVE and PROFESSIONAL academic report for the following student:
            
            STUDENT NAME: {student.name}
            REGISTRATION NUMBER: {student.registration_number}
            DEPARTMENT: {student.department}
            ATTENDANCE: {student.attendance}%
            
            PERFORMANCE SUMMARY:
            - Average Assignment Score: {avg_sub:.1f}%
            - Average Exam Score: {avg_exam:.1f}%
            
            DETAILED ASSIGNMENTS:
            {chr(10).join(sub_details) if sub_details else "No assignments recorded."}
            
            DETAILED EXAMS:
            {chr(10).join(exam_details) if exam_details else "No exams recorded."}
            
            REPORT STRUCTURE:
            1. Introduction: Briefly mention the student's background and general standing.
            2. Academic Performance: Detailed analysis of assignment and exam performance.
            3. Attendance & Engagement: Discuss the student's commitment based on their {student.attendance}% attendance.
            4. Strengths: Identify specific areas where the student is excelling.
            5. Areas for Improvement: Provide constructive feedback on where to focus.
            6. Conclusion & Recommendations: Final word for the parents/student.
            
            Tone: Professional, encouraging, and detailed. Do not use placeholders.
            """
            
            message = GroqService._client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=DEFAULT_MODEL,
                temperature=0.7,
                max_tokens=1500,
            )
            report.content = message.choices[0].message.content
            report.status = "ready"
            await report.save()

        elif type == 'Class Report':
            course = await Course.find_one(Course.int_id == target_id)
            if not course:
                report.status = "failed"
                report.content = "Course not found"
                await report.save()
                return
            
            # Fetch class stats
            students = await Student.find(Student.course_id == course.int_id).to_list()
            total_students = len(students)
            avg_attendance = sum([s.attendance for s in students])/total_students if total_students > 0 else 0
            
            prompt = f"""
            Generate a DETAILED Class-Level Analytical Report for the following course:
            
            COURSE: {course.name}
            TOTAL STUDENTS: {total_students}
            AVERAGE ATTENDANCE: {avg_attendance:.1f}%
            
            REPORT STRUCTURE:
            1. Executive Summary: Overall performance of the batch.
            2. Engagement Analysis: How the attendance and participation looks across the class.
            3. Subjective Analysis: Common areas where the class is excelling and where common misconceptions lie.
            4. Future Roadmap: Recommended teaching strategies for the next month.
            
            Tone: Analytical, administrative, and strategic.
            """
            
            message = GroqService._client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=DEFAULT_MODEL,
                temperature=0.7,
                max_tokens=1500,
            )
            report.content = message.choices[0].message.content
            report.status = "ready"
            await report.save()
            
        else:
            report.status = "ready"
            report.content = "Analytics export data generated."
            await report.save()
            
    except Exception as e:
        report.status = "failed"
        report.content = str(e)
        await report.save()

@report_router.post("/generate")
async def generate_report(req: GenerateReportRequest, background_tasks: BackgroundTasks):
    prefix = "RC" if req.type == 'Class Report' else "RS" if req.type == 'Student Report' else "RX"
    report_id = f"{prefix}-{str(uuid.uuid4())[:6].upper()}"
    
    name = f"Generated {req.type}"
    if req.type == 'Student Report':
        student = await Student.find_one(Student.int_id == req.target_id)
        if student:
            name = f"Parent-Ready Report: {student.name}"
    elif req.type == 'Class Report':
        course = await Course.find_one(Course.int_id == req.target_id)
        if course:
            name = f"Class Report - {course.name}"
            
    new_report = Report(
        report_id=report_id,
        name=name,
        type=req.type,
        status="generating",
        target_id=req.target_id
    )
    await new_report.assign_id()
    await new_report.insert()
    
    background_tasks.add_task(generate_report_background, new_report.int_id, req.type, req.target_id)
    
    return {"message": "Report generation started", "report_id": report_id}

@report_router.post("/{report_id}/send")
async def send_report(report_id: str, req: SendReportRequest, background_tasks: BackgroundTasks):
    report = await Report.find_one(Report.report_id == report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report.status != 'ready':
        raise HTTPException(status_code=400, detail="Report is not ready yet")
        
    student_name = "Student"
    if report.type == 'Student Report' and report.target_id:
        student = await Student.find_one(Student.int_id == report.target_id)
        if student:
            student_name = student.name

    subject = f"Academic Report for {student_name}" if report.type == 'Student Report' else f"{report.name}"
    body = f"Hello,\n\nPlease find the attached report:\n\n{report.content}\n\nBest Regards,\nTeacherBuddy"
    
    background_tasks.add_task(send_email, req.email, subject, body)
    return {"message": f"Report sent successfully to {req.email}"}


# ---------------------------------------------------------------------------
# Template-based report generation
# ---------------------------------------------------------------------------

UPLOAD_BASE = Path(__file__).resolve().parents[2] / "uploads"
EVENT_REPORT_TEMPLATE = Path(__file__).resolve().parents[3] / "docs" / "report template.docx"

ALLOWED_TEMPLATE_SUFFIXES = (".docx",)


async def _read_template_upload(template_file: UploadFile) -> tuple[bytes, str]:
    filename = template_file.filename or "template.pdf"
    if not filename.lower().endswith(ALLOWED_TEMPLATE_SUFFIXES):
        raise HTTPException(status_code=400, detail="Upload the editable DOCX template so its formatting can be preserved exactly.")
    return await template_file.read(), filename


@report_router.post("/scan-template")
async def scan_template(
    template_file: UploadFile = File(...),
    meeting_notes: str = Form(""),
    target_id: Optional[int] = Form(None),
    target_type: str = Form("auto"),
):
    """Inspect a DOCX template before any report is created."""
    content, filename = await _read_template_upload(template_file)
    try:
        result = ReportTemplateService.scan_template_fields(content, filename)
        template = ReportTemplateService.extract_template_from_bytes(content, filename)
        data = await ReportTemplateService.fetch_data_for_fields(template, target_type, target_id)
        result["preview_mapping"] = {
            field: (data.get(field) if data.get(field) and not str(data.get(field)).startswith("[DATA NOT FOUND") else result["preview_mapping"].get(field, ""))
            for field in result["fields_detected"]
        }
        result["fields_requiring_teacher"] = ReportTemplateService.required_fields(template, data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not scan template: {exc}") from exc
    result["meeting_notes"] = meeting_notes
    return result


@report_router.post("/generate-event")
async def generate_event_report(
    meeting_notes: str = Form(...),
    target_id: Optional[int] = Form(None),
):
    """Generate an activity report from notes using the fixed university template."""
    if not EVENT_REPORT_TEMPLATE.exists():
        raise HTTPException(status_code=500, detail="The fixed activity report template is missing from the deployment.")
    try:
        docx_bytes, fields_requiring_teacher = await ReportTemplateService.generate_event_report_from_notes(
            EVENT_REPORT_TEMPLATE.read_bytes(), meeting_notes
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Event report generation failed: {exc}") from exc

    output_dir = UPLOAD_BASE / "generated_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    output_path = output_dir / f"{token}_event_report.docx"
    output_path.write_bytes(docx_bytes)
    report_id = f"ER-{str(uuid.uuid4())[:6].upper()}"
    report = Report(
        report_id=report_id,
        name="Event Report",
        type="Event Report",
        status="ready",
        target_id=target_id,
        template_path="/docs/report template.docx",
        docx_path=f"/uploads/generated_reports/{output_path.name}",
        content="Activity report generated from meeting/event notes using the university template.",
    )
    await report.assign_id()
    await report.insert()
    return {
        "message": "Event report generated",
        "report_id": report_id,
        "status": "ready",
        "fields_requiring_teacher": fields_requiring_teacher,
    }


@report_router.post("/generate-manual")
async def generate_manual_report(
    template_file: UploadFile = File(...),
    meeting_notes: str = Form(""),
    field_overrides: str = Form("{}"),
    target_id: Optional[int] = Form(None),
    target_type: str = Form("auto"),
):
    """Generate and store a teacher-confirmed manual report immediately."""
    content, filename = await _read_template_upload(template_file)
    try:
        overrides = json.loads(field_overrides or "{}")
        if not isinstance(overrides, dict):
            raise ValueError("field_overrides must be a JSON object")
        docx_bytes = await ReportTemplateService.generate_with_overrides(
            content,
            filename,
            meeting_notes=meeting_notes,
            field_overrides=overrides,
            target_type=target_type,
            target_id=target_id,
        )
        template = ReportTemplateService.extract_template_from_bytes(content, filename)
        generated_data = await ReportTemplateService.fetch_data_for_fields(template, target_type, target_id)
        generated_data.update(overrides)
        required_fields = ReportTemplateService.required_fields(template, generated_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid field overrides: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc

    template_dir = UPLOAD_BASE / "report_templates"
    output_dir = UPLOAD_BASE / "generated_reports"
    template_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    template_path = template_dir / f"{token}_{filename.replace(' ', '_')}"
    output_path = output_dir / f"{token}_manual_report.docx"
    template_path.write_bytes(content)
    output_path.write_bytes(docx_bytes)

    report_id = f"MR-{str(uuid.uuid4())[:6].upper()}"
    report = Report(
        report_id=report_id,
        name="Manual Report",
        type="Manual Report",
        status="ready",
        target_id=target_id,
        template_path=f"/uploads/report_templates/{template_path.name}",
        docx_path=f"/uploads/generated_reports/{output_path.name}",
        content="Teacher-confirmed report generated from the uploaded template.",
    )
    await report.assign_id()
    await report.insert()
    return {
        "message": "Manual report generated",
        "report_id": report_id,
        "status": "ready",
        "filename": output_path.name,
        "preview": {"fields": overrides, "meeting_notes": meeting_notes},
        "fields_requiring_teacher": required_fields,
    }

async def generate_from_template_background(report_db_id: int, pdf_path: str, target_id: int | None):
    """Background task: run the full template pipeline and save DOCX."""
    report = await Report.find_one(Report.int_id == report_db_id)
    if not report:
        return

    try:
        # Read the uploaded PDF
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        # Run the pipeline
        docx_bytes = await ReportTemplateService.generate_report_from_template(
            pdf_bytes=pdf_bytes,
            target_id=target_id,
        )

        # Save DOCX to disk
        docx_filename = f"{uuid.uuid4().hex}_report.docx"
        docx_dir = UPLOAD_BASE / "generated_reports"
        docx_dir.mkdir(parents=True, exist_ok=True)
        docx_disk_path = docx_dir / docx_filename

        with open(docx_disk_path, "wb") as f:
            f.write(docx_bytes)

        report.docx_path = f"/uploads/generated_reports/{docx_filename}"
        report.status = "ready"
        report.content = "Report generated from template. Download the DOCX file."
        await report.save()

    except RuntimeError as e:
        # Groq unavailable or pipeline error
        report.status = "failed"
        report.content = str(e)
        await report.save()
    except Exception as e:
        report.status = "failed"
        report.content = f"Report generation failed: {str(e)}"
        await report.save()


@report_router.post("/generate-from-template")
async def generate_report_from_template(
    background_tasks: BackgroundTasks,
    template_file: UploadFile = File(...),
    target_id: Optional[int] = Form(None),
):
    """
    Upload a PDF report template. The system extracts its structure,
    fills fields with MongoDB data, uses Groq for prose sections,
    and generates a downloadable DOCX.
    """
    # Validate file type
    if not template_file.filename or not template_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted as templates.")

    # Pre-check Groq availability before doing any work
    if not ReportTemplateService.check_groq_available():
        raise HTTPException(
            status_code=503,
            detail="Groq AI service is currently unavailable. Cannot generate report content. Please try again later."
        )

    # Save uploaded PDF
    safe_name = f"{uuid.uuid4().hex}_{template_file.filename.replace(' ', '_')}"
    template_dir = UPLOAD_BASE / "report_templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    pdf_disk_path = template_dir / safe_name

    content = await template_file.read()
    with open(pdf_disk_path, "wb") as f:
        f.write(content)

    # Create report DB record
    report_id = f"RT-{str(uuid.uuid4())[:6].upper()}"

    # Build a descriptive name
    name = "Template Report"
    if target_id:
        student = await Student.find_one(Student.int_id == target_id)
        if student:
            name = f"Template Report: {student.name}"
        else:
            course = await Course.find_one(Course.int_id == target_id)
            if course:
                name = f"Template Report: {course.name}"

    new_report = Report(
        report_id=report_id,
        name=name,
        type="Template Report",
        status="generating",
        target_id=target_id,
        template_path=f"/uploads/report_templates/{safe_name}",
    )
    await new_report.assign_id()
    await new_report.insert()

    # Launch background generation
    background_tasks.add_task(
        generate_from_template_background,
        new_report.int_id,
        str(pdf_disk_path),
        target_id,
    )

    return {"message": "Template report generation started", "report_id": report_id}


@report_router.get("/{report_id}/download")
async def download_report(report_id: str):
    """Download the generated DOCX file for a report."""
    report = await Report.find_one(Report.report_id == report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != "ready":
        raise HTTPException(status_code=400, detail="Report is not ready yet")

    if not report.docx_path:
        raise HTTPException(status_code=404, detail="No DOCX file available for this report")

    # Resolve the disk path
    # docx_path is like "/uploads/generated_reports/abc123_report.docx"
    relative = report.docx_path.lstrip("/")
    disk_path = Path(__file__).resolve().parents[2] / relative

    if not disk_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    filename = f"{report.name.replace(' ', '_')}.docx"
    return FileResponse(
        path=str(disk_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
