from fastapi import APIRouter
from app.models.student import Student
from app.models.course import Course
from app.models.history import ActionHistory
from app.models.exam import Exam
from app.models.appointment import Appointment
from app.models.omr import OMRSubmission
from app.models.submission import Submission
from app.models.lesson import Lesson
from app.models.assignment import Assignment
from app.models.calendar import CalendarEvent
from datetime import datetime, date, timedelta
from typing import Optional

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

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
    ]
    if not value: return None
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None

@dashboard_router.get("/summary")
async def get_dashboard_summary(teacher_name: Optional[str] = None):
    # 1. Stats
    student_query = Student.find_all()
    teacher_course_ids = []
    if teacher_name:
        teacher_courses = await Course.find(Course.teacher_name == teacher_name).to_list()
        teacher_course_ids = [c.int_id for c in teacher_courses]
        student_query = student_query.find({"course_id": {"$in": teacher_course_ids}})
    
    total_students = await student_query.count()
    students = await student_query.to_list()
    
    # AI Evaluations Done: Count OMR submissions
    omr_evals = await OMRSubmission.find(OMRSubmission.status == "verified").count()
    
    # Deltas (last 7 days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    # Beanie query using ISO formatted date if stored as string, or datetime if stored as datetime
    new_evals = await OMRSubmission.find({"created_at": {"$gte": seven_days_ago}}).count()
    
    new_student_actions = await ActionHistory.find(
        ActionHistory.feature == "student",
        ActionHistory.action == "create",
        {"timestamp": {"$gte": seven_days_ago}}
    ).count()

    student_delta = f"+{new_student_actions}" if new_student_actions > 0 else "0%"

    real_risk_alerts = []
    for s in students:
        att = s.attendance or 0
        avg = s.avg_score or 0
        if 0 < att < 50:
            real_risk_alerts.append({"id": f"S{s.int_id}", "name": s.name or "Unknown", "level": "high", "reason": f"Attendance dropped to {att}%", "score": avg})
        elif 0 < avg < 40:
            real_risk_alerts.append({"id": f"S{s.int_id}", "name": s.name or "Unknown", "level": "high", "reason": f"Average score is critically low ({avg}%)", "score": avg})
        elif 0 < att < 75:
            real_risk_alerts.append({"id": f"S{s.int_id}", "name": s.name or "Unknown", "level": "moderate", "reason": f"Low attendance ({att}%)", "score": avg})
        elif 0 < avg < 60:
            real_risk_alerts.append({"id": f"S{s.int_id}", "name": s.name or "Unknown", "level": "moderate", "reason": f"Below average score ({avg}%)", "score": avg})
            
    risk_alerts_count = len(real_risk_alerts)
    
    # Avg. Score Improvement calculation
    omr_subs = await OMRSubmission.find(OMRSubmission.status == "verified").to_list()
    all_omr_scores = [sub.score for sub in omr_subs]
    
    subs = await Submission.find(Submission.grade != None).to_list()
    all_submission_grades = [sub.grade for sub in subs if sub.grade is not None]
    
    total_scores = all_omr_scores + all_submission_grades
    
    if total_scores:
        current_avg = sum(total_scores) / len(total_scores)
        baseline_avg = sum(s.avg_score or 0 for s in students) / len(students) if students else 0
        if baseline_avg > 0:
            improvement = ((current_avg - baseline_avg) / baseline_avg) * 100
            avg_improvement = f"{improvement:+.1f}%"
        else:
            avg_improvement = "0%"
    else:
        avg_improvement = "0%"

    stats = [
        {
            "label": "Active Students",
            "value": f"{total_students:,}",
            "delta": student_delta,
            "icon": "Users",
            "color": "#264796",
            "bg": "rgba(38,71,150,0.1)",
            "accent": "border-l-[#264796]"
        },
        {
            "label": "Risk Alerts",
            "value": str(risk_alerts_count),
            "delta": f"{risk_alerts_count} active",
            "icon": "AlertTriangle",
            "color": "#dc2626",
            "bg": "rgba(220,38,38,0.1)",
            "accent": "border-l-red-500"
        },
        {
            "label": "Avg. Score Improvement",
            "value": avg_improvement,
            "delta": "vs baseline",
            "icon": "TrendingUp",
            "color": "#16a34a",
            "bg": "rgba(22,163,74,0.1)",
            "accent": "border-l-green-500"
        },
    ]

    # 2. Ongoing Classrooms
    courses_query = Course.find_all()
    if teacher_name:
        courses_query = courses_query.find(Course.teacher_name == teacher_name)
    
    courses_list = await courses_query.limit(4).to_list()
    classrooms = []
    for i, c in enumerate(courses_list):
        latest_lesson = await Lesson.find(Lesson.course_id == c.int_id).sort("-posted_at").first_or_none()
        time_str = "09:00 AM"
        if latest_lesson and latest_lesson.posted_at:
            time_str = latest_lesson.posted_at.strftime("%I:%M %p")
        else:
            times = ["09:00 AM", "11:30 AM", "02:00 PM", "04:30 PM"]
            time_str = times[i % len(times)]

        real_count = await Student.find(Student.course_id == c.int_id).count()

        classrooms.append({
            "id": c.int_id,
            "code": c.code,
            "name": c.name,
            "batch": c.batch,
            "students": real_count,
            "time": time_str,
            "progress": c.progress or 0,
            "teacher": c.teacher_name or "Not Assigned"
        })

    real_risk_alerts.sort(key=lambda x: (0 if x["level"] == "high" else 1, x["score"]))
    risk_alerts = real_risk_alerts[:4]
    
    # 4. Recent Activity
    history_records = await ActionHistory.find_all().sort("-timestamp").limit(4).to_list()
    recent_activity = []
    
    color_map = {
        "mail": "#264796",
        "appointment": "#16a34a",
        "calendar": "#d0ae61",
        "omr": "#dc2626",
        "default": "#264796"
    }
    
    icon_map = {
        "mail": "BookOpen",
        "appointment": "CheckCircle2",
        "calendar": "Calendar",
        "omr": "BrainCircuit",
        "default": "Activity"
    }
    
    for h in history_records:
        recent_activity.append({
            "text": f"{h.feature.capitalize()}: {h.action.replace('_', ' ')}",
            "time": format_relative_time(h.timestamp),
            "icon": icon_map.get(h.feature, icon_map["default"]),
            "color": color_map.get(h.feature, color_map["default"])
        })

    # 5. Today's Schedule
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)
    
    schedule_items = []

    # 5a. Appointments
    appt_query = Appointment.find_all()
    if teacher_name:
        appt_query = appt_query.find(Appointment.teacher_name == teacher_name)
    
    for appt in await appt_query.to_list():
        dt = _parse_date_safe(appt.time_slot)
        if not dt:
            dt = _parse_date_safe(appt.requested_at)
            
        if appt.status == "rejected":
            continue
            
        if dt and today_start <= dt < today_end:
            schedule_items.append({
                "name": appt.agenda or "Meeting",
                "code": "APT",
                "course_id": getattr(appt, 'course_id', None),
                "time": dt,
                "room": appt.meeting_mode or "Office",
                "status": "upcoming"
            })

    # 5b. Lessons & Courses
    courses_query = Course.find_all()
    if teacher_name:
        courses_query = courses_query.find(Course.teacher_name == teacher_name)
    teacher_courses = await courses_query.to_list()
    teacher_course_ids = [c.int_id for c in teacher_courses]
    courses_map = {c.int_id: c for c in teacher_courses}

    lesson_query = Lesson.find_all()
    if teacher_name:
        lesson_query = lesson_query.find({"course_id": {"$in": teacher_course_ids}})
    
    today_lessons = await lesson_query.find(
        {"posted_at": {"$gte": today_start, "$lt": today_end}}
    ).to_list()
    
    for lesson in today_lessons:
        course = courses_map.get(lesson.course_id)
        schedule_items.append({
            "name": lesson.title or lesson.topic,
            "code": course.code if course else "CLASS",
            "course_id": lesson.course_id,
            "time": lesson.posted_at,
            "room": "Lecture Hall",
            "status": "live" if 0 < (datetime.now() - lesson.posted_at).total_seconds() < 3600 else "upcoming"
        })

    # 5c. Calendar Events
    try:
        ce_query = CalendarEvent.find(
            {"start_time": {"$gte": today_start, "$lt": today_end}}
        )
        if teacher_name:
            ce_query = ce_query.find(CalendarEvent.teacher_name == teacher_name)
            
        today_events = await ce_query.to_list()
        for ev in today_events:
            schedule_items.append({
                "name": ev.title,
                "code": "EVENT",
                "time": ev.start_time,
                "room": ev.location or "Campus",
                "status": "live" if ev.start_time <= datetime.now() <= ev.end_time else "upcoming"
            })
    except:
        pass

    # 5d. Assignments Due Today
    assg_query = Assignment.find_all()
    if teacher_name:
        assg_query = assg_query.find({"course_id": {"$in": teacher_course_ids}})
    
    for assg in await assg_query.to_list():
        dt = _parse_date_safe(assg.due_date)
        if dt and today_start <= dt < today_end:
            course = courses_map.get(assg.course_id)
            schedule_items.append({
                "name": f"Due: {assg.title}",
                "code": course.code if course else "DUE",
                "time": dt,
                "room": "Submission",
                "status": "upcoming"
            })

    # 5e. Exams Today
    for exam in await Exam.find_all().to_list():
        if teacher_name and exam.course_id not in teacher_course_ids:
            continue
        dt = exam.created_at
        if dt and today_start <= dt < today_end:
            course = courses_map.get(exam.course_id)
            schedule_items.append({
                "name": f"Exam: {exam.title}",
                "code": course.code if course else "EXAM",
                "time": dt,
                "room": "Online",
                "status": "upcoming"
            })

    # Sort by time
    schedule_items.sort(key=lambda x: x["time"])
    
    schedule = []
    for item in schedule_items[:5]:
        schedule.append({
            "name": item["name"],
            "code": item["code"],
            "course_id": item.get("course_id"),
            "time": item["time"].strftime("%I:%M %p"),
            "room": item["room"],
            "status": item["status"]
        })

    return {
        "stats": stats,
        "classrooms": classrooms,
        "riskAlerts": risk_alerts,
        "recentActivity": recent_activity,
        "schedule": schedule
    }

@dashboard_router.get("/discoverable-classrooms")
async def get_discoverable_classrooms():
    """Return classrooms that students can discover and join from EduGames."""
    courses = await Course.find_all().to_list()
    discoverable = [course for course in courses if course.enrollment_code]

    classrooms = []
    for course in discoverable:
        classroom = course.model_dump()
        classroom["id"] = course.int_id
        classroom["students"] = await Student.find(Student.course_id == course.int_id).count()
        classroom["progress"] = 0
        classroom["color"] = classroom.get("color") or "#264796"
        classroom["description"] = classroom.get("description") or ""
        classrooms.append(classroom)
    return classrooms


@dashboard_router.get("/student-summary")
async def get_student_dashboard_summary(student_name: str = "Aarav Gupta"):
    # 1. Student Info & Stats
    student_records = await Student.find(Student.name == student_name).to_list()
    course_ids = [s.course_id for s in student_records]
    
    avg_score = 0
    if student_records:
        avg_score = sum((s.avg_score or 0) for s in student_records) / len(student_records)
    
    # GPA = avg_score / 25 (rough mapping 0-100 to 0-4.0)
    gpa = round(avg_score / 25, 1) if avg_score > 0 else 0.0
    level = int(avg_score / 10) + 1 if avg_score > 0 else 1
    
    # 2. Enrolled Courses
    courses = await Course.find({"int_id": {"$in": course_ids}}).to_list() if course_ids else []
    
    # 3. Pending Assignments & Deadlines
    all_assignments = await Assignment.find({"course_id": {"$in": course_ids}}).to_list() if course_ids else []
    
    upcoming_deadlines = []
    pending_count = 0
    
    # Fetch student submissions
    from app.models.submission import Submission
    student_submissions = await Submission.find(Submission.student_name == student_name).to_list()
    submitted_assignment_ids = {sub.assignment_id for sub in student_submissions if sub.submitted_at}
    
    today = datetime.now()
    for assign in all_assignments:
        if assign.int_id in submitted_assignment_ids:
            continue
        due_dt = _parse_date_safe(assign.due_date)
        if due_dt and due_dt > today:
            c = await Course.find_one(Course.int_id == assign.course_id)
            upcoming_deadlines.append({
                "id": assign.int_id,
                "title": assign.title,
                "course_code": c.code if c else "UNK",
                "course_id": assign.course_id,
                "due_date": assign.due_date,
                "is_urgent": (due_dt - today).days < 2
            })
            pending_count += 1
    
    # 4. Live Games
    from app.models.game import ChainAnswerGame
    from app.models.user import User
    live_games = await ChainAnswerGame.find(ChainAnswerGame.status == "active").to_list()
    
    live_game_info = {
        "title": "Interactive Learning Session",
        "teacher": "Academic Faculty",
        "active": False
    }
    
    if live_games:
        game = live_games[0]
        teacher_name = "Prof. Alan Turing"
        if game.teacher_id:
            teacher = await User.find_one(User.int_id == game.teacher_id)
            if teacher:
                teacher_name = teacher.full_name or teacher.username
        
        live_game_info = {
            "title": game.name or "Live Quiz Session",
            "teacher": teacher_name,
            "active": True
        }
    
    return {
        "student": {
            "name": student_name,
            "gpa": gpa,
            "level": level,
            "pendingAssignments": pending_count,
            "liveGames": len(live_games)
        },
        "courses": [
            {
                "id": c.int_id,
                "code": c.code,
                "name": c.name,
                "teacher_name": c.teacher_name,
                "students": c.students,
                "batch": c.batch,
                "progress": getattr(c, 'progress', 0.0),
                "description": getattr(c, 'description', ''),
                "enrollment_code": getattr(c, 'enrollment_code', None),
                "course_plan_path": getattr(c, 'course_plan_path', None),
                "color": getattr(c, 'color', '#3b82f6')
            } for c in courses
        ],
        "deadlines": upcoming_deadlines[:5],
        "liveGame": live_game_info
    }

def format_relative_time(dt):
    if not dt:
        return "Unknown"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            dt = dt.replace(tzinfo=None) # remove tz for comparison
        except:
            return dt
            
    now = datetime.now()
    diff = now - dt
    if diff.days > 0:
        return f"{diff.days}d ago"
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes}m ago"
    return "Just now"
