from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.models.exam import ExamAttempt, Exam
from app.models.submission import Submission
from app.models.assignment import Assignment
from app.models.student import Student
from app.models.user import User
from app.models.course import Course
from typing import List, Optional
import pandas as pd
import io
import numpy as np
from datetime import datetime
import json

analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/risk-global")
async def get_global_risk(teacher_name: str = ""):
    """Return risk intelligence for every course owned by a teacher."""
    if not teacher_name.strip():
        raise HTTPException(status_code=400, detail="teacher_name is required")

    courses = await Course.find(Course.teacher_name == teacher_name).to_list()
    course_ids = [course.int_id for course in courses]
    students = await Student.find({"course_id": {"$in": course_ids}}).to_list() if course_ids else []

    avg_attendance = sum(float(student.attendance or 0) for student in students) / len(students) if students else 0
    avg_score = sum(float(student.avg_score or 0) for student in students) / len(students) if students else 0
    risk_students = []
    for student in students:
        attendance = float(student.attendance or 0)
        score = float(student.avg_score or 0)
        is_risk = score < 40 or attendance < 50 or score < 55 or attendance < 75
        if is_risk:
            risk_students.append({
                "id": student.registration_number or f"ST-{student.int_id}",
                "name": student.name or "Unknown Student",
                "course_id": student.course_id,
                "attendance": attendance,
                "avgScore": score,
                "assignments": 0,
                "risk": round(100 - (score + attendance) / 2),
                "level": "high" if score < 40 or attendance < 50 else "moderate",
            })

    risk_students.sort(key=lambda student: student["risk"], reverse=True)
    return {
        "overview": {
            "avg_score": f"{avg_score:.1f}%",
            "total_students": len(students),
            "at_risk_count": len(risk_students),
            "attendance_rate": f"{avg_attendance:.1f}%",
        },
        "avg_score": avg_score,
        "avg_attendance": avg_attendance,
        "at_risk_count": len(risk_students),
        "risk_students": risk_students,
        "course_count": len(courses),
    }

@analytics_router.get("/course/{course_id}")
async def get_course_analytics(course_id: int):
    # Get all exams for the course
    exams = await Exam.find(Exam.course_id == course_id).to_list()
    
    # Get all assignments for the course
    assignments = await Assignment.find(Assignment.course_id == course_id).to_list()
    assignment_ids = [a.int_id for a in assignments]
    
    # Get all submissions for these assignments
    submissions = await Submission.find({"assignment_id": {"$in": assignment_ids}}).to_list()
    
    all_data = []
    
    for e in exams:
        max_score = sum(q.points for q in e.questions) if e.questions else 100
        for a in e.attempts:
            if a.status == "submitted":
                user = await User.find_one(User.int_id == a.student_id)
                student = await Student.find_one(Student.email == user.email) if user else None
                student_name = student.name if student else (user.name if user else "Unknown")
                
                score_pct = (a.score / max_score * 100) if max_score > 0 and a.score is not None else 0
                all_data.append({
                    "student_id": a.student_id,
                    "student_name": student_name,
                    "score": score_pct,
                    "type": "exam",
                    "item_id": e.int_id,
                    "title": e.title or "Unknown Exam",
                    "date": a.end_time
                })
    
    for s in submissions:
        assignment = next((a for a in assignments if a.int_id == s.assignment_id), None)
        title = assignment.title if assignment else "Unknown Assignment"
        max_score = assignment.max_points if assignment and getattr(assignment, 'max_points', None) else 100
        if s.grade is not None:
            score_pct = (s.grade / max_score * 100) if max_score > 0 else 0
            try:
                date_val = datetime.strptime(s.submitted_at, "%I:%M %p, %b %d")
                date_val = date_val.replace(year=datetime.now().year)
            except:
                date_val = datetime.now()

            all_data.append({
                "student_id": None, 
                "student_name": s.student_name,
                "score": score_pct,
                "type": "assignment",
                "item_id": s.assignment_id,
                "title": title,
                "date": date_val
            })

    if not all_data:
        return {
            "overview": {
                "avg_score": "0%",
                "total_students": 0,
                "at_risk_count": 0,
                "attendance_rate": "0%",
                "pass_rate": "0%",
                "high_score": "0%",
                "low_score": "0%"
            },
            "risk_students": [],
            "performance_trend": [],
            "subject_breakdown": []
        }

    df = pd.DataFrame(all_data)
    avg_score = df["score"].mean()
    pass_rate = (df["score"] >= 40).mean() * 100 
    
    student_avgs = df.groupby('student_name')['score'].mean()
    
    # Calculate actual attendance average for the course
    all_students = await Student.find(Student.course_id == course_id).to_list()
    if all_students:
        avg_attendance = sum(s.attendance or 0 for s in all_students) / len(all_students)
    else:
        avg_attendance = 0
    
    at_risk_count = 0
    risk_list = []
    assignment_submission_counts = {}
    for submission in submissions:
        if submission.student_name:
            assignment_submission_counts[submission.student_name] = assignment_submission_counts.get(submission.student_name, 0) + 1
    assignment_total = len(assignments)
    
    # Identify at-risk students based on BOTH score and attendance
    for s in all_students:
        s_avg = student_avgs.get(s.name, 0)
        s_att = s.attendance or 0
        
        is_risk = False
        if s_avg < 40:
            is_risk = True
        elif s_att < 50:
            is_risk = True
        elif s_avg < 55 or s_att < 75:
            is_risk = True # Moderate risk
            
        if is_risk:
            at_risk_count += 1
            risk_list.append({
                "id": s.registration_number or f"ST-{s.int_id}",
                "name": s.name,
                "attendance": s_att,
                "avgScore": float(s_avg),
                "assignments": round((assignment_submission_counts.get(s.name, 0) / assignment_total) * 100, 1) if assignment_total else 0,
                "risk": int(100 - (s_avg + s_att)/2), 
                "level": "high" if (s_avg < 40 or s_att < 50) else "moderate"
            })
    
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%b')
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    trend_df = df.groupby('month')['score'].mean().reindex(month_order).dropna().reset_index()
    trend = trend_df.replace([np.inf, -np.inf], 0).fillna(0).to_dict(orient='records')

    subject_stats = []
    for e in exams:
        exam_scores = df[(df['type'] == 'exam') & (df['item_id'] == e.int_id)]['score']
        if not exam_scores.empty:
            subject_stats.append({
                "subject": e.title,
                "avg": float(exam_scores.mean())
            })

    raw_list = []
    for d in all_data:
        raw_list.append({
            "Student": d["student_name"],
            "Score": float(d["score"]),
            "Exam": d["title"],
            "Date": d["date"].strftime("%b %d, %Y") if isinstance(d["date"], datetime) else str(d["date"])
        })

    return {
        "overview": {
            "avg_score": f"{avg_score:.1f}%",
            "total_students": len(all_students),
            "at_risk_count": at_risk_count,
            "attendance_rate": f"{avg_attendance:.1f}%",
            "pass_rate": f"{pass_rate:.0f}%",
            "high_score": f"{df['score'].max():.1f}%",
            "low_score": f"{df['score'].min():.1f}%"
        },
        "risk_students": risk_list,
        "performance_trend": trend,
        "subject_breakdown": subject_stats,
        "raw_data": raw_list
    }

@analytics_router.post("/upload")
async def upload_analytics_data(
    file: UploadFile = File(...),
    impute_method: str = Form("auto")
):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    id_keywords = ['id', 'reg', 'number', 'roll', 'serial', 'sn', 'index', 'phone', 'mobile', 'code', 'year', 'semester']
    valid_numeric_cols = [c for c in numeric_cols if not any(k in c for k in id_keywords)]
    
    # Track missing values before imputation
    missing_before = int(df[valid_numeric_cols].isna().sum().sum()) if len(valid_numeric_cols) > 0 else 0

    if impute_method == "blank":
        # "Keep Blank" / Hide imputation: only replace inf, preserve NaN
        df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
    elif impute_method == "auto" or impute_method == "zero":
        for col in valid_numeric_cols:
            if any(k in col for k in ['total', 'sum', 'grand', 'final']):
                components = [c for c in valid_numeric_cols if any(k in c for k in ['score', 'exam', 'quiz', 'assign', 'mid', 'final', 'test']) and c != col]
                if components:
                    df[col] = df[col].fillna(df[components].sum(axis=1))
                else:
                    df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna(0)
        df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan).fillna(0)
    elif impute_method == "mean":
        df[valid_numeric_cols] = df[valid_numeric_cols].fillna(df[valid_numeric_cols].mean().fillna(0))
        df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan).fillna(0)

    missing_after = int(df[valid_numeric_cols].isna().sum().sum()) if len(valid_numeric_cols) > 0 else 0

    score_col = None
    priority_keywords = ['grand_total', 'final_score', 'total_marks', 'total', 'final', 'score', 'marks', 'percentage']
    for kw in priority_keywords:
        matching = [c for c in df.columns if kw in c]
        if matching:
            for m in matching:
                if m in valid_numeric_cols:
                    score_col = m
                    break
        if score_col: break
    
    if not score_col and valid_numeric_cols:
        score_col = valid_numeric_cols[0]

    attendance_col = next((column for column in df.columns if column in {"attendance", "attendance_rate", "attendance_percentage"} or "attendance" in column), None)
    avg_attendance = float(df[attendance_col].mean(skipna=True)) if attendance_col and df[attendance_col].notna().any() else None
    
    if score_col:
        max_val = df[score_col].max(skipna=True)
        scale = 100
        if 0 < max_val <= 10: scale = 10
        elif 10 < max_val <= 20: scale = 20
        elif 20 < max_val <= 50: scale = 50
        
        normalized_series = (df[score_col] / scale) * 100
        # Use skipna for NaN-safe aggregations
        avg_score = float(df[score_col].mean(skipna=True)) if df[score_col].notna().any() else 0.0
        std_dev = float(df[score_col].std(skipna=True)) if df[score_col].notna().sum() > 1 else 0.0
        non_null_normalized = normalized_series.dropna()
        pass_rate = float((non_null_normalized >= 40).mean() * 100) if len(non_null_normalized) > 0 else 0.0
        
        # Grading Distribution (only for non-null scores)
        bins = [0, 40, 45, 50, 55, 60, 70, 80, 101]
        labels = ['F (Fail)', 'P (Pass)', 'C (Fair)', 'B (Satisfactory)', 'B+ (Good)', 'A (Very Good)', 'A+ (Excellent)', 'O (Outstanding)']
        df['grade_group'] = pd.cut(normalized_series, bins=bins, labels=labels, right=False)
        df['grade_group'] = df['grade_group'].astype(str)
        distribution = df['grade_group'].value_counts().to_dict()
        total_graded = sum(v for k, v in distribution.items() if k != 'nan')
        dist_list = [{"grade": k, "pct": int((v / total_graded) * 100) if total_graded > 0 else 0, "count": int(v)} for k, v in distribution.items() if k != 'nan']
        
        # Student List for Bell Curve
        name_col = 'name' if 'name' in df.columns else 'student_name' if 'student_name' in df.columns else df.columns[0]
        roll_col = 'id' if 'id' in df.columns else 'roll_no' if 'roll_no' in df.columns else 'roll' if 'roll' in df.columns else df.columns[1] if len(df.columns) > 1 else 'N/A'
        
        student_points = []
        for _, row in df.iterrows():
            score_val = row[score_col]
            # Skip students with missing scores for bell curve (they have no data to plot)
            if pd.isna(score_val):
                continue
            student_points.append({
                "name": str(row.get(name_col, 'Unknown')),
                "roll": str(row.get(roll_col, 'N/A')),
                "score": float(score_val)
            })

        risk_students = []
        # Filter only non-null scores for risk assessment
        risk_mask = normalized_series < 50
        risk_mask = risk_mask & normalized_series.notna()
        for _, row in df[risk_mask].iterrows():
            score_val = row[score_col]
            if pd.isna(score_val):
                continue
            risk_students.append({
                "id": str(row.get(roll_col, 'N/A')),
                "name": str(row.get(name_col, 'Unknown')),
                "avgScore": float(score_val),
                "attendance": float(row[attendance_col]) if attendance_col and pd.notna(row.get(attendance_col)) else None,
                "risk": int(100 - (score_val/scale)*100),
                "level": "high" if (score_val/scale)*100 < 40 else "moderate"
            })

        # Also flag students with missing score data as "data-missing" risk
        if impute_method == "blank":
            missing_score_mask = df[score_col].isna()
            for _, row in df[missing_score_mask].iterrows():
                risk_students.append({
                    "id": str(row.get(roll_col, 'N/A')),
                    "name": str(row.get(name_col, 'Unknown')),
                    "avgScore": 0,
                    "attendance": float(row[attendance_col]) if attendance_col and pd.notna(row.get(attendance_col)) else None,
                    "risk": 100,
                    "level": "high",
                    "missing_data": True
                })
    else:
        avg_score, std_dev, pass_rate, scale = 0, 0, 0, 100
        dist_list, student_points, risk_students = [], [], []
        missing_before, missing_after = 0, 0

    # Prepare raw_data: replace NaN with None for JSON compatibility
    raw_df = df.head(100).copy()
    # Drop the grade_group helper column if it exists
    if 'grade_group' in raw_df.columns:
        raw_df = raw_df.drop(columns=['grade_group'])
    raw_data = json.loads(raw_df.to_json(orient='records'))

    # Safely compute high/low scores
    if score_col and df[score_col].notna().any():
        high_score = f"{df[score_col].max(skipna=True):.1f}"
        low_score = f"{df[score_col].min(skipna=True):.1f}"
    else:
        high_score, low_score = "0", "0"

    return {
        "summary": {
            "rows": len(df),
            "columns": [c for c in df.columns if c != 'grade_group'],
            "score_column": score_col,
            "scale": scale,
            "avg_score": f"{avg_score:.1f}",
            "std_dev": std_dev if not (isinstance(std_dev, float) and np.isnan(std_dev)) else 0,
            "pass_rate": f"{pass_rate:.0f}%",
            "high_score": high_score,
            "low_score": low_score,
            "attendance_column": attendance_col,
            "avg_attendance": round(avg_attendance, 1) if avg_attendance is not None else None,
            "missing_values": missing_after,
            "impute_method": impute_method
        },
        "distribution": dist_list,
        "risk_students": risk_students,
        "student_points": student_points,
        "raw_data": raw_data
    }
