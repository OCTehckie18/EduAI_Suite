"""
Calendar routes – aggregate assignments, exams, appointments, lessons,
and custom teacher events into a unified calendar feed.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.calendar import CalendarEvent

# ── Pydantic Schemas ─────────────────────────────────────────
class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    event_type: str = "custom"
    color: str = "#264796"
    location: Optional[str] = None
    is_all_day: bool = False
    recurrence: Optional[str] = None
    teacher_name: Optional[str] = None
    student_email: Optional[str] = None
    course_id: Optional[int] = None


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    event_type: Optional[str] = None
    color: Optional[str] = None
    location: Optional[str] = None
    is_all_day: Optional[bool] = None
    recurrence: Optional[str] = None
    recurrence: Optional[str] = None
    teacher_name: Optional[str] = None
    student_email: Optional[str] = None
    course_id: Optional[int] = None


calendar_router = APIRouter(prefix="/calendar", tags=["Calendar"])


def _parse_date_safe(value: str) -> Optional[datetime]:
    """Try multiple date formats."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


@calendar_router.get("/events")
async def get_calendar_events(
    start: Optional[str] = None,
    end: Optional[str] = None,
    teacher_name: Optional[str] = None,
    student_email: Optional[str] = None,
):
    """
    Return all calendar events (custom + aggregated from other tables)
    within an optional date range.
    """
    from app.models.assignment import Assignment
    from app.models.exam import Exam
    from app.models.appointment import Appointment
    from app.models.lesson import Lesson
    from app.models.course import Course
    from app.models.student import Student

    range_start = _parse_date_safe(start) if start else datetime.utcnow() - timedelta(days=90)
    range_end = _parse_date_safe(end) if end else datetime.utcnow() + timedelta(days=90)

    student_course_ids = []
    if student_email:
        student_records = await Student.find(Student.email == student_email).to_list()
        student_course_ids = [s.course_id for s in student_records if s.course_id]

    events: List[dict] = []

    # ── Custom events ────────────────────────────────────────
    custom_query = CalendarEvent.find_all()
    if range_start:
        custom_query = custom_query.find(CalendarEvent.start_time >= range_start)
    if range_end:
        custom_query = custom_query.find(CalendarEvent.start_time <= range_end)
    if teacher_name:
        custom_query = custom_query.find(CalendarEvent.teacher_name == teacher_name)
    # Omit strict student_email filtering for custom events for demo reliability
    # if student_email:
    #     custom_query = custom_query.find(CalendarEvent.student_email == student_email)

    custom_events = await custom_query.to_list()
    for ev in custom_events:
        events.append({
            "id": f"custom-{ev.int_id}",
            "raw_id": ev.int_id,
            "title": ev.title,
            "description": ev.description or "",
            "start": ev.start_time.isoformat(),
            "end": ev.end_time.isoformat(),
            "type": ev.event_type,
            "color": ev.color,
            "location": ev.location or "",
            "is_all_day": ev.is_all_day,
            "source": "custom",
            "editable": True,
        })

    # ── Assignment deadlines ─────────────────────────────────
    courses = await Course.find_all().to_list()
    courses_map = {c.int_id: c for c in courses}

    assignments = await Assignment.find_all().to_list()
    for assg in assignments:
        dt = _parse_date_safe(assg.due_date) if assg.due_date else None
        if not dt:
            continue
        if range_start and dt < range_start:
            continue
        if range_end and dt > range_end:
            continue
        course = courses_map.get(assg.course_id)
        if teacher_name and course and course.teacher_name != teacher_name:
            continue
        if student_email and assg.course_id not in student_course_ids:
            continue
        events.append({
            "id": f"assignment-{assg.int_id}",
            "raw_id": assg.int_id,
            "title": f"📝 Due: {assg.title}",
            "description": assg.description or "",
            "start": dt.isoformat(),
            "end": (dt + timedelta(hours=1)).isoformat(),
            "type": "deadline",
            "color": "#d97706",
            "location": course.name if course else "",
            "is_all_day": False,
            "source": "assignment",
            "editable": False,
        })

    # ── Exams ────────────────────────────────────────────────
    exams = await Exam.find_all().to_list()
    for exam in exams:
        dt = exam.created_at
        if not dt:
            continue
        if range_start and dt < range_start:
            continue
        if range_end and dt > range_end:
            continue
        course = courses_map.get(exam.course_id)
        if teacher_name and course and course.teacher_name != teacher_name:
            continue
        if student_email and exam.course_id not in student_course_ids:
            continue
        events.append({
            "id": f"exam-{exam.int_id}",
            "raw_id": exam.int_id,
            "title": f"📋 Exam: {exam.title}",
            "description": exam.description or "",
            "start": dt.isoformat(),
            "end": (dt + timedelta(minutes=exam.time_limit or 60)).isoformat(),
            "type": "exam",
            "color": "#dc2626",
            "location": course.name if course else "",
            "is_all_day": False,
            "source": "exam",
            "editable": False,
        })

    # ── Appointments ─────────────────────────────────────────
    appointments = await Appointment.find_all().to_list()
    for appt in appointments:
        dt = _parse_date_safe(appt.time_slot) if appt.time_slot else None
        if not dt:
            dt = _parse_date_safe(appt.requested_at) if appt.requested_at else None
            
        if not dt:
            continue
            
        if appt.status == "rejected":
            continue
            
        if range_start and dt < range_start:
            continue
        if range_end and dt > range_end:
            continue
        if teacher_name and appt.teacher_name != teacher_name:
            continue
        # Omit strict student_email filtering for single-tenant demo reliability
        # if student_email and appt.student_email != student_email:
        #     continue
        status_colors = {"pending": "#d97706", "approved": "#16a34a", "rejected": "#dc2626"}
        events.append({
            "id": f"appointment-{appt.int_id}",
            "raw_id": appt.int_id,
            "title": f"👤 {appt.student_name}: {appt.agenda}",
            "description": f"Mode: {appt.meeting_mode} | Booked for: {appt.time_slot}",
            "start": dt.isoformat(),
            "end": (dt + timedelta(minutes=30)).isoformat(),
            "type": "appointment",
            "color": status_colors.get(appt.status, "#264796"),
            "location": appt.meeting_mode or "",
            "is_all_day": False,
            "source": "appointment",
            "editable": False,
            "status": appt.status,
        })

    # ── Lessons ──────────────────────────────────────────────
    lessons = await Lesson.find_all().to_list()
    for lesson in lessons:
        dt = lesson.posted_at or lesson.created_at
        if not dt:
            continue
        if range_start and dt < range_start:
            continue
        if range_end and dt > range_end:
            continue
        course = courses_map.get(lesson.course_id)
        if teacher_name and course and course.teacher_name != teacher_name:
            continue
        if student_email and lesson.course_id not in student_course_ids:
            continue
        events.append({
            "id": f"lesson-{lesson.int_id}",
            "raw_id": lesson.int_id,
            "title": f"📖 {lesson.title or lesson.topic}",
            "description": lesson.topic,
            "start": dt.isoformat(),
            "end": (dt + timedelta(hours=1)).isoformat(),
            "type": "class",
            "color": "#7c3aed",
            "location": course.name if course else "",
            "is_all_day": False,
            "source": "lesson",
            "editable": False,
        })

    # Sort by start time
    events.sort(key=lambda e: e["start"])
    return events


@calendar_router.post("/events")
async def create_calendar_event(payload: CalendarEventCreate):
    """Create a new custom calendar event."""
    start_dt = _parse_date_safe(payload.start_time)
    end_dt = _parse_date_safe(payload.end_time)
    if not start_dt or not end_dt:
        raise HTTPException(status_code=400, detail="Invalid date format")

    event = CalendarEvent(
        title=payload.title,
        description=payload.description,
        start_time=start_dt,
        end_time=end_dt,
        event_type=payload.event_type,
        color=payload.color,
        location=payload.location,
        is_all_day=payload.is_all_day,
        recurrence=payload.recurrence,
        teacher_name=payload.teacher_name,
        student_email=payload.student_email,
        course_id=payload.course_id,
    )
    await event.assign_id()
    await event.insert()

    return {
        "id": f"custom-{event.int_id}",
        "raw_id": event.int_id,
        "title": event.title,
        "start": event.start_time.isoformat(),
        "end": event.end_time.isoformat(),
        "type": event.event_type,
        "color": event.color,
        "source": "custom",
        "editable": True,
    }


@calendar_router.put("/events/{event_id}")
async def update_calendar_event(event_id: int, payload: CalendarEventUpdate):
    """Update a custom calendar event."""
    event = await CalendarEvent.find_one(CalendarEvent.int_id == event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if payload.title is not None:
        event.title = payload.title
    if payload.description is not None:
        event.description = payload.description
    if payload.start_time is not None:
        dt = _parse_date_safe(payload.start_time)
        if dt:
            event.start_time = dt
    if payload.end_time is not None:
        dt = _parse_date_safe(payload.end_time)
        if dt:
            event.end_time = dt
    if payload.event_type is not None:
        event.event_type = payload.event_type
    if payload.color is not None:
        event.color = payload.color
    if payload.location is not None:
        event.location = payload.location
    if payload.is_all_day is not None:
        event.is_all_day = payload.is_all_day
    if payload.recurrence is not None:
        event.recurrence = payload.recurrence
    if payload.teacher_name is not None:
        event.teacher_name = payload.teacher_name
    if payload.student_email is not None:
        event.student_email = payload.student_email
    if payload.course_id is not None:
        event.course_id = payload.course_id

    await event.save()
    return {
        "id": f"custom-{event.int_id}",
        "raw_id": event.int_id,
        "title": event.title,
        "start": event.start_time.isoformat(),
        "end": event.end_time.isoformat(),
        "type": event.event_type,
        "color": event.color,
        "source": "custom",
        "editable": True,
    }


@calendar_router.delete("/events/{event_id}")
async def delete_calendar_event(event_id: int):
    """Delete a custom calendar event."""
    event = await CalendarEvent.find_one(CalendarEvent.int_id == event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await event.delete()
    return {"deleted": True, "id": event_id}


@calendar_router.get("/notifications")
async def get_calendar_notifications(teacher_name: Optional[str] = None, student_email: Optional[str] = None):
    """
    Return events happening tomorrow (24h window) for in-app reminders.
    Aggregates from all sources just like /events.
    """
    from app.models.assignment import Assignment
    from app.models.exam import Exam
    from app.models.appointment import Appointment
    from app.models.lesson import Lesson
    from app.models.course import Course

    from app.models.student import Student

    now = datetime.utcnow()
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow_start + timedelta(days=1)

    student_course_ids = []
    if student_email:
        student_records = await Student.find(Student.email == student_email).to_list()
        student_course_ids = [s.course_id for s in student_records if s.course_id]

    notifications: List[dict] = []

    # Custom events tomorrow
    custom_query = CalendarEvent.find(
        CalendarEvent.start_time >= tomorrow_start,
        CalendarEvent.start_time < tomorrow_end,
    )
    if teacher_name:
        custom_query = custom_query.find(CalendarEvent.teacher_name == teacher_name)
        
    custom_events = await custom_query.to_list()
    for ev in custom_events:
        notifications.append({
            "id": f"custom-{ev.int_id}",
            "title": ev.title,
            "start": ev.start_time.isoformat(),
            "type": ev.event_type,
            "color": ev.color,
            "source": "custom",
            "message": f"📅 Tomorrow: {ev.title} at {ev.start_time.strftime('%I:%M %p')}",
        })

    # Assignment deadlines tomorrow
    courses = await Course.find_all().to_list()
    courses_map = {c.int_id: c for c in courses}
    
    assignments = await Assignment.find_all().to_list()
    for assg in assignments:
        dt = _parse_date_safe(assg.due_date) if assg.due_date else None
        if dt and tomorrow_start <= dt < tomorrow_end:
            course = courses_map.get(assg.course_id)
            if teacher_name and course and course.teacher_name != teacher_name:
                continue
            if student_email and assg.course_id not in student_course_ids:
                continue
            notifications.append({
                "id": f"assignment-{assg.int_id}",
                "title": f"📝 Due: {assg.title}",
                "start": dt.isoformat(),
                "type": "deadline",
                "color": "#d97706",
                "source": "assignment",
                "message": f"📝 Assignment \"{assg.title}\" is due tomorrow" + (f" ({course.name})" if course else ""),
            })

    # Exams tomorrow
    exams = await Exam.find_all().to_list()
    for exam in exams:
        dt = exam.created_at
        if dt and tomorrow_start <= dt < tomorrow_end:
            course = courses_map.get(exam.course_id)
            if teacher_name and course and course.teacher_name != teacher_name:
                continue
            if student_email and exam.course_id not in student_course_ids:
                continue
            notifications.append({
                "id": f"exam-{exam.int_id}",
                "title": f"📋 Exam: {exam.title}",
                "start": dt.isoformat(),
                "type": "exam",
                "color": "#dc2626",
                "source": "exam",
                "message": f"📋 Exam \"{exam.title}\" is scheduled for tomorrow" + (f" ({course.name})" if course else ""),
            })

    # Appointments tomorrow
    appointments = await Appointment.find_all().to_list()
    for appt in appointments:
        dt = _parse_date_safe(appt.time_slot) if appt.time_slot else None
        if not dt:
            dt = _parse_date_safe(appt.requested_at) if appt.requested_at else None
            
        if dt and tomorrow_start <= dt < tomorrow_end:
            if appt.status == "rejected":
                continue
            if teacher_name and appt.teacher_name != teacher_name:
                continue
            if student_email and appt.student_email != student_email:
                continue
            notifications.append({
                "id": f"appointment-{appt.int_id}",
                "title": f"👤 {appt.student_name}: {appt.agenda}",
                "start": dt.isoformat(),
                "type": "appointment",
                "color": "#16a34a",
                "source": "appointment",
                "message": f"👤 Meeting with {appt.student_name} about \"{appt.agenda}\" tomorrow",
            })

    # Lessons tomorrow
    lessons = await Lesson.find_all().to_list()
    for lesson in lessons:
        dt = lesson.posted_at or lesson.created_at
        if dt and tomorrow_start <= dt < tomorrow_end:
            course = courses_map.get(lesson.course_id)
            if teacher_name and course and course.teacher_name != teacher_name:
                continue
            if student_email and lesson.course_id not in student_course_ids:
                continue
            notifications.append({
                "id": f"lesson-{lesson.int_id}",
                "title": f"📖 {lesson.title or lesson.topic}",
                "start": dt.isoformat(),
                "type": "class",
                "color": "#7c3aed",
                "source": "lesson",
                "message": f"📖 Lesson \"{lesson.title or lesson.topic}\" is scheduled for tomorrow" + (f" ({course.name})" if course else ""),
            })

    notifications.sort(key=lambda n: n["start"])
    return {"count": len(notifications), "notifications": notifications}
