from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from datetime import datetime
from app.models.student import Student
from app.models.course import Course
from app.models.mail import MailDraft, MailHistory
from app.models.history import ActionHistory
from app.utils.email_utils import send_email
from pydantic import BaseModel
from typing import List, Optional, Any
import pandas as pd
import io
import re

mail_router = APIRouter(prefix="/mail", tags=["Mailing"])

class Condition(BaseModel):
    field: str
    operator: str
    value: Any

class FilterRequest(BaseModel):
    conditions: List[Condition]

class DraftCreate(BaseModel):
    subject: str
    body: str
    student_ids: Optional[List[int]] = None
    conditions: Optional[List[dict]] = None

class TemporaryStudent(BaseModel):
    id: int
    name: str
    email: str
    registration_number: str
    attendance: float
    avg_score: float

class SendMailRequest(BaseModel):
    student_ids: Optional[List[int]] = []
    temporary_students: Optional[List[TemporaryStudent]] = []
    subject: Optional[str] = None
    body: Optional[str] = None
    draft_ids: Optional[List[int]] = None

@mail_router.post("/preview_upload")
async def preview_upload(file: UploadFile = File(...)):
    content = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
    df.columns = df.columns.str.strip().str.lower()
    
    def get_val(row, possible_names, default=""):
        for name in possible_names:
            if name in row.index:
                val = row[name]
                return default if pd.isna(val) else val
        return default

    preview_data = []
    
    for idx, row in df.head(10).iterrows():
        try:
            att_val = int(float(get_val(row, ['att', 'attendance', 'attendance (%)', 'attendance%'], 0)))
        except ValueError:
            att_val = 0
            
        try:
            marks_val = int(float(get_val(row, ['marks', 'score', 'average marks', 'avg_score', 'total marks'], 0)))
        except ValueError:
            marks_val = 0

        preview_data.append({
            "registration_number": str(get_val(row, ['reg', 'registration number', 'reg no', 'register number', 'roll no', 'reg_no', 'registration_number'])),
            "name": str(get_val(row, ['name', 'student name', 'full name', 'student_name'])),
            "email": str(get_val(row, ['email', 'email address', 'email id', 'email_address'])),
            "course_name": str(get_val(row, ['course', 'program', 'degree', 'course_id'], 'Default Course')),
            "attendance": att_val,
            "avg_score": marks_val
        })
        
    return {
        "total_records": len(df),
        "preview": preview_data
    }

@mail_router.post("/upload_students")
async def upload_students(file: UploadFile = File(...)):
    content = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
    # Normalize headers
    df.columns = df.columns.str.strip().str.lower()
    
    def get_val(row, possible_names, default=""):
        for name in possible_names:
            if name in row.index:
                val = row[name]
                return default if pd.isna(val) else val
        return default

    # await Student.find_all().delete() # removed for temporary data behavior
    
    students_to_insert = []
    temp_id_start = 9000000
    
    for idx, row in df.iterrows():
        course_name = str(get_val(row, ['course', 'program', 'degree', 'course_id'], 'Default Course'))
        if not course_name or course_name.lower() == 'nan':
            course_name = 'Default Course'
            
        course = await Course.find_one(Course.name == course_name)
        if not course:
            course = Course(name=course_name, code=course_name[:6].upper(), batch="2026", students=0, progress=0)
            await course.assign_id()
            await course.insert()
            
        try:
            att_val = int(float(get_val(row, ['att', 'attendance', 'attendance (%)', 'attendance%'], 0)))
        except ValueError:
            att_val = 0
            
        try:
            marks_val = int(float(get_val(row, ['marks', 'score', 'average marks', 'avg_score', 'total marks'], 0)))
        except ValueError:
            marks_val = 0

        student_dict = {
            "id": temp_id_start + idx,
            "registration_number": str(get_val(row, ['reg', 'registration number', 'reg no', 'register number', 'roll no', 'reg_no', 'registration_number'])),
            "name": str(get_val(row, ['name', 'student name', 'full name', 'student_name'])),
            "email": str(get_val(row, ['email', 'email address', 'email id', 'email_address'])),
            "course_id": course.int_id if course else 0,
            "department": str(get_val(row, ['dept', 'department'])),
            "attendance": att_val,
            "avg_score": marks_val,
            "student_class": "2026"
        }
        students_to_insert.append(student_dict)
        
    return {"message": "Data parsed successfully", "data": students_to_insert}

@mail_router.post("/filter")
async def filter_students(req: FilterRequest):
    # Construct Beanie query dynamically
    query = Student.find_all()
    
    for cond in req.conditions:
        # Prevent access to non-existent or internal fields
        if not hasattr(Student, cond.field) or cond.field.startswith('_'):
            continue
            
        field = getattr(Student, cond.field)
        op = cond.operator
        val = cond.value
        
        if op == "==":
            query = query.find(field == val)
        elif op == "!=":
            query = query.find(field != val)
        elif op == ">":
            query = query.find(field > val)
        elif op == "<":
            query = query.find(field < val)
        elif op == ">=":
            query = query.find(field >= val)
        elif op == "<=":
            query = query.find(field <= val)
        elif op == "contains":
            # MongoDB regex equivalent for ilike
            query = query.find({cond.field: {"$regex": val, "$options": "i"}})
            
    students = await query.to_list()
    # add `id` field mapped from `int_id` for backward compatibility
    res = []
    for s in students:
        s_dict = s.model_dump()
        s_dict["id"] = s.int_id
        res.append(s_dict)
    return res

@mail_router.get("/drafts")
async def get_drafts():
    return await MailDraft.find_all().sort("-int_id").to_list()

@mail_router.post("/drafts")
async def create_draft(req: DraftCreate):
    draft = MailDraft(subject=req.subject, body=req.body, student_ids=req.student_ids, conditions=req.conditions)
    await draft.assign_id()
    await draft.insert()
    
    # Return backward-compatible response
    res = draft.model_dump()
    res["id"] = draft.int_id
    return res

@mail_router.put("/drafts/{draft_id}")
async def update_draft(draft_id: int, req: DraftCreate):
    draft = await MailDraft.find_one(MailDraft.int_id == draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.subject = req.subject
    draft.body = req.body
    draft.student_ids = req.student_ids
    draft.conditions = req.conditions
    await draft.save()
    
    res = draft.model_dump()
    res["id"] = draft.int_id
    return res

@mail_router.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: int):
    draft = await MailDraft.find_one(MailDraft.int_id == draft_id)
    if draft:
        await draft.delete()
    return {"message": "Deleted"}

@mail_router.get("/history")
async def get_history():
    return await MailHistory.find_all().sort("-sent_at").to_list()

@mail_router.post("/send")
async def send_bulk_mail(req: SendMailRequest, background_tasks: BackgroundTasks):
    db_students = []
    if req.student_ids:
        db_students = await Student.find({"int_id": {"$in": req.student_ids}}).to_list()
        
    all_students_data = [{"id": s.int_id, "name": s.name, "email": s.email, "registration_number": s.registration_number, "attendance": s.attendance, "avg_score": s.avg_score} for s in db_students]
    
    if req.temporary_students:
        for ts in req.temporary_students:
            all_students_data.append({
                "id": ts.id,
                "name": ts.name,
                "email": ts.email,
                "registration_number": ts.registration_number,
                "attendance": ts.attendance,
                "avg_score": ts.avg_score
            })
            
    if not all_students_data:
        raise HTTPException(status_code=404, detail="No students found for the given IDs or temporary list")

    mails_to_send = []
    
    if req.draft_ids and len(req.draft_ids) > 0:
        drafts = await MailDraft.find({"int_id": {"$in": req.draft_ids}}).to_list()
        for draft in drafts:
            mails_to_send.append({"subject": draft.subject, "body": draft.body})
    elif req.subject and req.body:
        mails_to_send.append({"subject": req.subject, "body": req.body})
    else:
        raise HTTPException(status_code=400, detail="Provide draft_ids or subject/body")

    sent_count = 0
    recipients_data = [{"id": s["id"], "name": s["name"], "email": s["email"]} for s in all_students_data]

    for mail_item in mails_to_send:
        history = MailHistory(
            subject=mail_item["subject"],
            body=mail_item["body"],
            recipients=recipients_data,
            recipient_count=len(all_students_data)
        )
        await history.assign_id()
        await history.insert()
        
        for student in all_students_data:
            personalized_body = mail_item["body"].replace("{{name}}", student["name"]) \
                                        .replace("{{reg_num}}", student["registration_number"]) \
                                        .replace("{{attendance}}", f"{student['attendance']}%") \
                                        .replace("{{marks}}", f"{student['avg_score']}%")
            
            background_tasks.add_task(send_email, student["email"], mail_item["subject"], personalized_body)
            sent_count += 1
            
    # Log to ActionHistory
    action_history = ActionHistory(
        feature="mail",
        action="send_bulk_mail",
        reaction="user_triggered",
        result=f"success_{sent_count}_recipients",
        timestamp=datetime.now(),
        metadata_json={
            "subject": mails_to_send[0]["subject"] if mails_to_send else "",
            "recipient_count": len(students),
            "draft_ids_used": req.draft_ids
        }
    )
    await action_history.assign_id()
    await action_history.insert()

    return {"message": f"Queued {sent_count} emails for sending"}
