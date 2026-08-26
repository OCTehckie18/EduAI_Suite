from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from app.models.appointment import Appointment
from app.models.history import ActionHistory
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentStatusUpdate
from app.models.user import User
from app.utils.auth import get_current_user

appointment_router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _same_identity(left: Optional[str], right: Optional[str]) -> bool:
    """Compare stored display names without case/whitespace drift."""
    normalize = lambda value: " ".join((value or "").split()).casefold()
    return bool(normalize(left)) and normalize(left) == normalize(right)


@appointment_router.get("/", response_model=list[AppointmentResponse])
async def get_appointments(
    teacher_name: Optional[str] = None,
    student_name: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    query = Appointment.find_all()
    if status_filter:
        query = query.find(Appointment.status == status_filter)
        
    appointments = await query.sort("-int_id").to_list()
    if current_user.role == "admin":
        pass
    elif current_user.role == "teacher":
        appointments = [a for a in appointments if _same_identity(a.teacher_name, current_user.name)]
    else:
        appointments = [a for a in appointments if a.student_email == current_user.email]
    return [AppointmentResponse(**{**a.model_dump(), "id": a.int_id}) for a in appointments]


@appointment_router.get("/teacher/{teacher_name}", response_model=list[AppointmentResponse])
async def get_teacher_appointments(
    teacher_name: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher" or not _same_identity(teacher_name, current_user.name):
        raise HTTPException(status_code=403, detail="You can only view your own appointments")
    appointments = await Appointment.find_all().sort("-int_id").to_list()
    appointments = [a for a in appointments if _same_identity(a.teacher_name, current_user.name)]
    return [AppointmentResponse(**{**a.model_dump(), "id": a.int_id}) for a in appointments]


@appointment_router.get("/student/{student_name}", response_model=list[AppointmentResponse])
async def get_student_appointments(
    student_name: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "teacher":
        raise HTTPException(status_code=403, detail="Teachers cannot view a student's private appointments")
    appointments = await Appointment.find(Appointment.student_email == current_user.email).sort("-int_id").to_list()
    return [AppointmentResponse(**{**a.model_dump(), "id": a.int_id}) for a in appointments]


@appointment_router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "teacher":
        raise HTTPException(status_code=403, detail="Only students can create appointment requests")

    # Store the teacher's canonical profile name instead of relying on the
    # display name supplied by the student-facing form.
    teachers = await User.find(User.role == "teacher").to_list()
    matched_teacher = next(
        (teacher for teacher in teachers if _same_identity(teacher.name, payload.teacher_name)),
        None,
    )
    canonical_teacher_name = matched_teacher.name if matched_teacher else payload.teacher_name

    appointment = Appointment(
        student_name=current_user.name or payload.student_name,
        student_email=current_user.email,
        teacher_name=canonical_teacher_name,
        teacher_department=payload.teacher_department,
        meeting_mode=payload.meeting_mode,
        time_slot=payload.time_slot,
        agenda=payload.agenda,
        details=payload.details,
        status="pending",
        requested_at=datetime.utcnow().isoformat(timespec="minutes"),
    )
    await appointment.assign_id()
    await appointment.insert()
    
    # Log to ActionHistory for notifications
    history = ActionHistory(
        feature="appointment",
        action="book_appointment",
        reaction="student_triggered",
        result="pending",
        timestamp=datetime.now(),
        metadata_json={
            "student_name": appointment.student_name,
            "teacher_name": appointment.teacher_name,
            "agenda": appointment.agenda,
            "time_slot": appointment.time_slot
        }
    )
    await history.assign_id()
    await history.insert()
    
    return AppointmentResponse(**{**appointment.model_dump(), "id": appointment.int_id})


@appointment_router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    current_user: User = Depends(get_current_user),
):
    appointment = await Appointment.find_one(Appointment.int_id == appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role != "admin" and (
        current_user.role != "teacher"
        or not _same_identity(appointment.teacher_name, current_user.name)
    ):
        raise HTTPException(status_code=403, detail="You can only manage your own appointments")

    appointment.status = payload.status
    appointment.reviewed_by = current_user.name
    appointment.reviewed_at = datetime.utcnow().isoformat(timespec="minutes")
    appointment.rejection_reason = payload.rejection_reason
    appointment.notes = payload.notes
    
    # Log to ActionHistory for notifications
    history = ActionHistory(
        feature="appointment",
        action=f"{payload.status}_appointment",
        reaction="teacher_triggered",
        result=payload.status,
        timestamp=datetime.now(),
        metadata_json={
            "appointment_id": appointment.int_id,
            "student_name": appointment.student_name,
            "status": payload.status,
            "rejection_reason": payload.rejection_reason
        }
    )
    await history.assign_id()
    await history.insert()
    
    await appointment.save()
    return AppointmentResponse(**{**appointment.model_dump(), "id": appointment.int_id})
