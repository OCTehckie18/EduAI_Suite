from fastapi import APIRouter, HTTPException
from app.models.student import Student
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.exam import Exam, ExamAttempt
from app.models.game import ChainAnswerGame
from app.models.course import Course
import logging
import random

logger = logging.getLogger(__name__)

engagement_router = APIRouter(prefix="/engagement", tags=["Engagement"])


def _compute_engagement_level(score: float) -> str:
    """Return engagement level label based on composite score (0-100)."""
    if score >= 75:
        return "excellent"
    elif score >= 55:
        return "good"
    elif score >= 35:
        return "needs_attention"
    else:
        return "at_risk"


def _generate_engagement_summary(student_name: str, engagement_data: dict) -> str:
    """Generate a deterministic engagement summary using rule-based heuristics."""

    attendance = engagement_data.get("attendance", 0)
    eng_score = engagement_data.get("engagement_score", 0)
    eng_level = engagement_data.get("engagement_level", "unknown")
    assign = engagement_data.get("assignments", {})
    exams = engagement_data.get("exams", {})
    games = engagement_data.get("games", {})

    has_data = (
        attendance > 0
        or assign.get("submitted", 0) > 0
        or exams.get("total_attempts", 0) > 0
        or games.get("sessions_played", 0) > 0
    )
    if not has_data:
        return ""

    parts = []

    # ── Engagement overview (with varied intros) ──────────────
    if eng_level == "excellent":
        intro = random.choice([
            f"{student_name} is performing exceptionally well",
            f"{student_name} demonstrates outstanding engagement",
            f"{student_name} continues to excel across all metrics",
        ])
        parts.append(f"{intro} with an engagement score of {eng_score}/100.")
    elif eng_level == "good":
        intro = random.choice([
            f"{student_name} shows solid engagement",
            f"{student_name} maintains a healthy engagement level",
            f"{student_name} is performing well overall",
        ])
        parts.append(f"{intro} at {eng_score}/100, with room for growth.")
    elif eng_level == "needs_attention":
        intro = random.choice([
            f"{student_name}'s engagement score of {eng_score}/100 indicates they may need additional support.",
            f"With a score of {eng_score}/100, {student_name} could benefit from closer monitoring.",
            f"{student_name} is showing signs of disengagement at {eng_score}/100 — proactive outreach is advised.",
        ])
        parts.append(intro)
    else:
        intro = random.choice([
            f"{student_name} is at risk with an engagement score of only {eng_score}/100 and requires immediate attention.",
            f"Urgent: {student_name} has dropped to {eng_score}/100 — intervention is strongly recommended.",
            f"{student_name}'s engagement has fallen critically to {eng_score}/100 — schedule a meeting as soon as possible.",
        ])
        parts.append(intro)

    # ── Attendance insight ────────────────────────────────────
    if attendance >= 80:
        parts.append(random.choice([
            f"Attendance is strong at {attendance}%.",
            f"Consistently present with {attendance}% attendance.",
        ]))
    elif attendance >= 50:
        parts.append(random.choice([
            f"Attendance of {attendance}% is below expectations — consider a check-in.",
            f"Attendance at {attendance}% needs improvement — a brief conversation may help.",
        ]))
    else:
        parts.append(random.choice([
            f"Critically low attendance at {attendance}% — this is the top priority to address.",
            f"Attendance has dropped to {attendance}% — immediate follow-up is essential.",
        ]))

    # ── Assignment insight ────────────────────────────────────
    total_a = assign.get("total", 0)
    submitted_a = assign.get("submitted", 0)
    if total_a > 0:
        rate = assign.get("completion_rate", 0)
        if rate >= 80:
            parts.append(random.choice([
                f"Assignment completion is excellent ({submitted_a}/{total_a}).",
                f"Submissions are on track — {submitted_a} of {total_a} assignments completed.",
            ]))
        elif rate >= 50:
            parts.append(random.choice([
                f"Has submitted {submitted_a} of {total_a} assignments — encourage timely submissions.",
                f"{submitted_a}/{total_a} assignments submitted — some deadlines were missed.",
            ]))
        else:
            parts.append(random.choice([
                f"Only {submitted_a} of {total_a} assignments submitted — follow up on missing work.",
                f"Significant gaps in submissions ({submitted_a}/{total_a}) — check for blockers.",
            ]))

    # ── Exam insight ──────────────────────────────────────────
    exam_attempts = exams.get("total_attempts", 0)
    avg_exam = exams.get("avg_score")
    if exam_attempts > 0 and avg_exam is not None:
        if avg_exam >= 70:
            parts.append(f"Exam performance is solid with an average of {avg_exam} across {exam_attempts} attempt(s).")
        elif avg_exam >= 40:
            parts.append(f"Exam average of {avg_exam} across {exam_attempts} attempt(s) suggests room for improvement.")
        else:
            parts.append(f"Low exam average of {avg_exam} — consider remedial support or retake opportunities.")

    # ── Games insight ─────────────────────────────────────────
    sessions = games.get("sessions_played", 0)
    if sessions > 0:
        parts.append(f"Participated in {sessions} EduGame session(s) with a total score of {games.get('total_score', 0)}.")

    return " ".join(parts)


async def _get_student_engagement(student: Student, assignments: list):
    """Compute engagement data for a single student within a course."""
    student_id_str = str(student.int_id)

    # ── Assignment / Submission data ──────────────────────────
    total_assignments = len(assignments)
    submissions = []
    submitted_count = 0
    total_grade = 0.0
    graded_count = 0

    for a in assignments:
        sub = await Submission.find_one(
            Submission.assignment_id == a.int_id,
            Submission.student_name == student.name
        )
        if sub:
            submitted_count += 1
            submissions.append({
                "assignment_id": a.int_id,
                "assignment_title": a.title,
                "due_date": a.due_date,
                "status": "submitted",
                "grade": sub.grade,
                "submitted_at": sub.submitted_at,
                "max_points": a.max_points,
            })
            if sub.grade is not None:
                total_grade += sub.grade
                graded_count += 1
        else:
            submissions.append({
                "assignment_id": a.int_id,
                "assignment_title": a.title,
                "due_date": a.due_date,
                "status": "missing",
                "grade": None,
                "submitted_at": None,
                "max_points": a.max_points,
            })

    assignment_completion = (submitted_count / total_assignments * 100) if total_assignments > 0 else 0
    avg_grade = (total_grade / graded_count) if graded_count > 0 else None

    # ── Exam data ─────────────────────────────────────────────
    exam_attempts_raw = []
    try:
        exam_attempts_raw = await ExamAttempt.find(
            ExamAttempt.student_id == student.int_id,
            ExamAttempt.status == "submitted"
        ).to_list()
    except Exception:
        pass

    exams_data = []
    total_exam_score = 0.0
    for attempt in exam_attempts_raw:
        exam = await Exam.find_one(Exam.int_id == attempt.exam_id)
        exam_title = exam.title if exam else "Unknown Exam"
        exams_data.append({
            "exam_id": attempt.exam_id,
            "exam_title": exam_title,
            "score": attempt.score,
            "status": attempt.status,
            "start_time": attempt.start_time.isoformat() if attempt.start_time else None,
            "end_time": attempt.end_time.isoformat() if attempt.end_time else None,
        })
        if attempt.score is not None:
            total_exam_score += attempt.score

    avg_exam_score = (total_exam_score / len(exam_attempts_raw)) if exam_attempts_raw else None

    # Find all games where this student participated
    games = await ChainAnswerGame.find({"players.student_id": student_id_str}).to_list()

    games_data = []
    total_game_score = 0.0
    total_words_submitted = 0
    total_words_valid = 0

    for game in games:
        # Find the specific player sub-document in this game
        gp = next((p for p in game.players if p.student_id == student_id_str), None)
        if gp:
            game_name = game.name if game.name else "Unknown Game"
            game_status = game.status if game.status else "unknown"
            games_data.append({
                "game_id": game.int_id,
                "game_name": game_name,
                "game_status": game_status,
                "score": gp.score,
                "words_submitted": gp.words_submitted,
                "words_valid": gp.words_valid,
                "player_status": gp.status,
            })
            total_game_score += (gp.score or 0)
            total_words_submitted += (gp.words_submitted or 0)
            total_words_valid += (gp.words_valid or 0)

    # ── Engagement Score ──────────────────────────────────────
    attendance_pct = min(student.attendance or 0, 100)
    assignment_score_pct = assignment_completion
    exam_pct = min(avg_exam_score or 0, 100) if avg_exam_score is not None else attendance_pct
    game_pct = min(total_game_score, 100) if games_data else attendance_pct

    engagement_score = round(
        attendance_pct * 0.25 +
        assignment_score_pct * 0.35 +
        exam_pct * 0.25 +
        game_pct * 0.15,
        1
    )

    engagement_level = _compute_engagement_level(engagement_score)

    # ── Activity Timeline ─────────────────────────────────────
    timeline = []

    for sub_data in submissions:
        if sub_data["status"] == "submitted" and sub_data["submitted_at"]:
            timeline.append({
                "type": "assignment_submission",
                "title": f"Submitted: {sub_data['assignment_title']}",
                "detail": f"Grade: {sub_data['grade']}" if sub_data['grade'] is not None else "Pending grading",
                "timestamp": sub_data["submitted_at"],
                "icon": "file-check"
            })

    for exam_d in exams_data:
        timeline.append({
            "type": "exam_attempt",
            "title": f"Exam: {exam_d['exam_title']}",
            "detail": f"Score: {exam_d['score']}",
            "timestamp": exam_d["end_time"] or exam_d["start_time"],
            "icon": "clipboard-list"
        })

    for game_d in games_data:
        timeline.append({
            "type": "game_session",
            "title": f"Game: {game_d['game_name']}",
            "detail": f"Score: {game_d['score']} | Words: {game_d['words_valid']}/{game_d['words_submitted']}",
            "timestamp": None,
            "icon": "gamepad-2"
        })

    timeline.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    result = {
        "student_id": student.int_id,
        "name": student.name,
        "email": student.email,
        "registration_number": student.registration_number,
        "department": student.department,
        "student_class": student.student_class,
        "attendance": student.attendance or 0,
        "engagement_score": engagement_score,
        "engagement_level": engagement_level,

        "assignments": {
            "total": total_assignments,
            "submitted": submitted_count,
            "completion_rate": round(assignment_completion, 1),
            "avg_grade": round(avg_grade, 1) if avg_grade is not None else None,
            "details": submissions,
        },

        "exams": {
            "total_attempts": len(exam_attempts_raw),
            "avg_score": round(avg_exam_score, 1) if avg_exam_score is not None else None,
            "details": exams_data,
        },

        "games": {
            "sessions_played": len(games_data),
            "total_score": total_game_score,
            "total_words_submitted": total_words_submitted,
            "total_words_valid": total_words_valid,
            "details": games_data,
        },

        "timeline": timeline[:20],
    }

    result["engagement_summary"] = _generate_engagement_summary(student.name, result)

    return result


@engagement_router.get("/{course_id}/summary")
async def get_course_engagement_summary(course_id: int):
    """Get engagement summary for all students in a course."""
    course = await Course.find_one(Course.int_id == course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    students = await Student.find(Student.course_id == course_id).to_list()
    assignments = await Assignment.find(Assignment.course_id == course_id).to_list()

    if not students:
        return {
            "course_id": course_id,
            "course_name": course.name,
            "total_students": 0,
            "class_avg_engagement": 0,
            "class_avg_attendance": 0,
            "class_avg_assignment_completion": 0,
            "at_risk_count": 0,
            "students": [],
        }

    all_engagement = []
    for s in students:
        eng = await _get_student_engagement(s, assignments)
        all_engagement.append(eng)

    total = len(all_engagement)
    avg_engagement = round(sum(e["engagement_score"] for e in all_engagement) / total, 1)
    avg_attendance = round(sum(e["attendance"] for e in all_engagement) / total, 1)
    avg_assignment = round(sum(e["assignments"]["completion_rate"] for e in all_engagement) / total, 1)
    at_risk = sum(1 for e in all_engagement if e["engagement_level"] == "at_risk")
    needs_attention = sum(1 for e in all_engagement if e["engagement_level"] == "needs_attention")

    all_engagement.sort(key=lambda x: x["engagement_score"], reverse=True)

    return {
        "course_id": course_id,
        "course_name": course.name,
        "total_students": total,
        "class_avg_engagement": avg_engagement,
        "class_avg_attendance": avg_attendance,
        "class_avg_assignment_completion": avg_assignment,
        "at_risk_count": at_risk,
        "needs_attention_count": needs_attention,
        "students": all_engagement,
    }


@engagement_router.get("/student/{student_id}")
async def get_student_engagement(student_id: int):
    """Get detailed engagement profile for a single student."""
    student = await Student.find_one(Student.int_id == student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    assignments = await Assignment.find(Assignment.course_id == student.course_id).to_list()

    return await _get_student_engagement(student, assignments)
