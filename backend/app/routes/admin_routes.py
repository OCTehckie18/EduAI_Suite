"""
Admin Routes
Handles admin functionality including user approvals, teacher/student management, and bulk operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
import csv
import io

from app.models.user import User, UserStatus, UserRole
from app.schemas.user_schema import (
    PendingUserResponse,
    ApprovalAction,
    WhitelistStudentRequest,
    TeacherResponse,
    StudentResponse,
    UserListResponse,
    BulkOperationResponse
)
from app.utils.auth import get_admin_user

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get(
    "/pending-approvals",
    response_model=List[PendingUserResponse],
)
async def list_pending_approvals(
    _admin: User = Depends(get_admin_user),
):
    """Return all users whose status is PENDING."""
    pending = await User.find(User.status == UserStatus.PENDING).sort("-int_id").to_list()
    res = []
    for p in pending:
        d = p.model_dump()
        d["id"] = p.int_id
        res.append(d)
    return res


@admin_router.patch("/approve-user/{user_id}")
async def approve_user(
    user_id: int,
    _admin: User = Depends(get_admin_user),
):
    """Set a user's status to APPROVED."""
    user = await User.find_one(User.int_id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status == UserStatus.APPROVED:
        return {"message": "User is already approved", "user_id": user_id}

    user.status = UserStatus.APPROVED
    await user.save()
    return {"message": "User approved successfully", "user_id": user_id}


from pydantic import BaseModel, EmailStr

class WhitelistStudentRequest(BaseModel):
    email: EmailStr


@admin_router.patch("/deny-user/{user_id}")
async def deny_user(
    user_id: int,
    body: ApprovalAction = None,
    _admin: User = Depends(get_admin_user),
):
    """Set a user's status to DENIED."""
    user = await User.find_one(User.int_id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = UserStatus.DENIED
    await user.save()
    return {
        "message": "User denied",
        "user_id": user_id,
        "reason": body.reason if body else None,
    }


@admin_router.post("/whitelist-email")
async def whitelist_email(
    body: WhitelistStudentRequest,
    _admin: User = Depends(get_admin_user),
):
    """Manually add a student email (any domain) that behaves as a new pending student."""
    email = body.email.strip().lower()

    # Check if a user with this email already exists
    existing = await User.find_one(User.email == email)
    if existing:
        if existing.role == "student":
            if existing.status != UserStatus.PENDING:
                existing.status = UserStatus.PENDING
                await existing.save()
            return {"message": "Email is already registered as a student (set to pending)", "user_id": existing.int_id}
        else:
            existing.role = "student"
            existing.status = UserStatus.PENDING
            await existing.save()
            return {"message": "Existing user converted to student (pending approval)", "user_id": existing.int_id}

    # Create a new student user in PENDING status
    new_user = User(
        name=email.split("@")[0].capitalize(),
        email=email,
        role="student",
        status=UserStatus.PENDING,
        hashed_password=None,
    )
    await new_user.assign_id()
    await new_user.insert()

    return {"message": "Email successfully whitelisted as pending student", "user_id": new_user.int_id}


# Teacher Management Endpoints
@admin_router.get("/teachers", response_model=UserListResponse)
async def list_teachers(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    _admin: User = Depends(get_admin_user),
):
    """List all teachers with filtering and pagination."""
    query = User.role == UserRole.TEACHER

    if search:
        query = query & (User.name.contains(search) | User.email.contains(search))
    if department:
        query = query & (User.department == department)
    if status:
        query = query & (User.status == status)

    # Get total count
    total = await User.find(query).count()

    # Get paginated results
    skip = (page - 1) * limit
    teachers = await User.find(query).skip(skip).limit(limit).sort("-int_id").to_list()

    # Convert to response format
    teacher_responses = []
    for teacher in teachers:
        d = teacher.model_dump()
        d["id"] = teacher.int_id
        teacher_responses.append(d)

    return UserListResponse(
        users=teacher_responses,
        total=total,
        page=page,
        limit=limit,
        has_next=(skip + limit) < total,
        has_prev=page > 1
    )


@admin_router.get("/teachers/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(
    teacher_id: int,
    _admin: User = Depends(get_admin_user),
):
    """Get specific teacher details."""
    teacher = await User.find_one(User.int_id == teacher_id, User.role == UserRole.TEACHER)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    d = teacher.model_dump()
    d["id"] = teacher.int_id
    return d


@admin_router.patch("/teachers/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(
    teacher_id: int,
    updates: dict,
    _admin: User = Depends(get_admin_user),
):
    """Update teacher information."""
    teacher = await User.find_one(User.int_id == teacher_id, User.role == UserRole.TEACHER)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Update only allowed fields
    allowed_fields = {"name", "email", "department", "employee_id", "registration_number"}
    for field, value in updates.items():
        if field in allowed_fields and value is not None:
            setattr(teacher, field, value)

    await teacher.save()

    d = teacher.model_dump()
    d["id"] = teacher.int_id
    return d


@admin_router.delete("/teachers/{teacher_id}")
async def delete_teacher(
    teacher_id: int,
    _admin: User = Depends(get_admin_user),
):
    """Delete/deactivate teacher (soft delete by setting status to DENIED)."""
    teacher = await User.find_one(User.int_id == teacher_id, User.role == UserRole.TEACHER)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    teacher.status = UserStatus.DENIED
    await teacher.save()
    return {"message": "Teacher deactivated successfully", "teacher_id": teacher_id}


# Student Management Endpoints
@admin_router.get("/students", response_model=UserListResponse)
async def list_students(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    registration_number: Optional[str] = None,
    status: Optional[str] = None,
    _admin: User = Depends(get_admin_user),
):
    """List all students with filtering and pagination."""
    query = User.role == UserRole.STUDENT

    if search:
        query = query & (User.name.contains(search) | User.email.contains(search))
    if registration_number:
        query = query & (User.registration_number == registration_number)
    if status:
        query = query & (User.status == status)

    # Get total count
    total = await User.find(query).count()

    # Get paginated results
    skip = (page - 1) * limit
    students = await User.find(query).skip(skip).limit(limit).sort("-int_id").to_list()

    # Convert to response format
    student_responses = []
    for student in students:
        d = student.model_dump()
        d["id"] = student.int_id
        student_responses.append(d)

    return UserListResponse(
        users=student_responses,
        total=total,
        page=page,
        limit=limit,
        has_next=(skip + limit) < total,
        has_prev=page > 1
    )


@admin_router.get("/students/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    _admin: User = Depends(get_admin_user),
):
    """Get specific student details."""
    student = await User.find_one(User.int_id == student_id, User.role == UserRole.STUDENT)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    d = student.model_dump()
    d["id"] = student.int_id
    return d


@admin_router.patch("/students/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: int,
    updates: dict,
    _admin: User = Depends(get_admin_user),
):
    """Update student information."""
    student = await User.find_one(User.int_id == student_id, User.role == UserRole.STUDENT)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Update only allowed fields
    allowed_fields = {"name", "email", "registration_number"}
    for field, value in updates.items():
        if field in allowed_fields and value is not None:
            setattr(student, field, value)

    await student.save()

    d = student.model_dump()
    d["id"] = student.int_id
    return d


@admin_router.delete("/students/{student_id}")
async def delete_student(
    student_id: int,
    _admin: User = Depends(get_admin_user),
):
    """Delete/deactivate student (soft delete by setting status to DENIED)."""
    student = await User.find_one(User.int_id == student_id, User.role == UserRole.STUDENT)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.status = UserStatus.DENIED
    await student.save()
    return {"message": "Student deactivated successfully", "student_id": student_id}


# Bulk Operations
@admin_router.post("/teachers/bulk", response_model=BulkOperationResponse)
async def bulk_upload_teachers(
    file: UploadFile = File(...),
    _admin: User = Depends(get_admin_user),
):
    """Bulk upload teachers from CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    contents = await file.read()
    csv_file = io.StringIO(contents.decode('utf-8'))
    reader = csv.DictReader(csv_file)

    processed = 0
    successful = 0
    failed = 0
    errors = []

    for row in reader:
        processed += 1
        try:
            # Check if user already exists
            existing = await User.find_one(User.email == row['email'])
            if existing:
                if existing.role == UserRole.TEACHER:
                    # Update existing teacher
                    for field in ['name', 'department', 'employee_id']:
                        if field in row and row[field]:
                            setattr(existing, field, row[field])
                    await existing.save()
                else:
                    # Convert to teacher
                    existing.role = UserRole.TEACHER
                    existing.status = UserStatus.APPROVED
                    existing.name = row.get('name', existing.name)
                    existing.email = row['email']
                    existing.department = row.get('department')
                    existing.employee_id = row.get('employee_id')
                    await existing.save()
            else:
                # Create new teacher
                new_teacher = User(
                    name=row.get('name', row['email'].split('@')[0].capitalize()),
                    email=row['email'],
                    role=UserRole.TEACHER,
                    status=UserStatus.APPROVED,
                    department=row.get('department'),
                    employee_id=row.get('employee_id'),
                    hashed_password=None,  # Will need to set password or use OAuth
                )
                await new_teacher.assign_id()
                await new_teacher.insert()

            successful += 1
        except Exception as e:
            failed += 1
            errors.append(f"Row {processed}: {str(e)}")

    return BulkOperationResponse(
        processed=processed,
        successful=successful,
        failed=failed,
        errors=errors
    )


@admin_router.post("/students/bulk", response_model=BulkOperationResponse)
async def bulk_upload_students(
    file: UploadFile = File(...),
    _admin: User = Depends(get_admin_user),
):
    """Bulk upload students from CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    contents = await file.read()
    csv_file = io.StringIO(contents.decode('utf-8'))
    reader = csv.DictReader(csv_file)

    processed = 0
    successful = 0
    failed = 0
    errors = []

    for row in reader:
        processed += 1
        try:
            # Check if user already exists
            existing = await User.find_one(User.email == row['email'])
            if existing:
                if existing.role == UserRole.STUDENT:
                    # Update existing student
                    if 'registration_number' in row and row['registration_number']:
                        existing.registration_number = row['registration_number']
                    await existing.save()
                else:
                    # Convert to student
                    existing.role = UserRole.STUDENT
                    existing.status = UserStatus.PENDING  # Start as pending for approval
                    existing.name = row.get('name', existing.name)
                    existing.email = row['email']
                    existing.registration_number = row.get('registration_number')
                    await existing.save()
            else:
                # Create new student
                new_student = User(
                    name=row.get('name', row['email'].split('@')[0].capitalize()),
                    email=row['email'],
                    role=UserRole.STUDENT,
                    status=UserStatus.PENDING,
                    registration_number=row.get('registration_number'),
                    hashed_password=None,
                )
                await new_student.assign_id()
                await new_student.insert()

            successful += 1
        except Exception as e:
            failed += 1
            errors.append(f"Row {processed}: {str(e)}")

    return BulkOperationResponse(
        processed=processed,
        successful=successful,
        failed=failed,
        errors=errors
    )


@admin_router.get("/users/export")
async def export_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    _admin: User = Depends(get_admin_user),
):
    """Export users to CSV."""
    query = {}
    if role:
        query["role"] = role
    if status:
        query["status"] = status

    users = await User.find(query).to_list()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['ID', 'Name', 'Email', 'Role', 'Status', 'Department', 'Employee ID', 'Registration Number'])

    # Data rows
    for user in users:
        writer.writerow([
            user.int_id,
            user.name or '',
            user.email,
            user.role or '',
            user.status or '',
            user.department or '',
            user.employee_id or '',
            user.registration_number or '',
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=users_export.csv"}
    )


# Dashboard Stats Endpoint
@admin_router.get("/dashboard-stats")
async def get_dashboard_stats(
    _admin: User = Depends(get_admin_user),
):
    """Get dashboard statistics for admin panel."""
    # Count total teachers
    total_teachers = await User.find(User.role == UserRole.TEACHER).count()

    # Count total students
    total_students = await User.find(User.role == UserRole.STUDENT).count()

    # Count pending approvals
    pending_approvals = await User.find(User.status == UserStatus.PENDING).count()

    # Count active users (approved)
    active_users = await User.find(User.status == UserStatus.APPROVED).count()

    return {
        "totalTeachers": total_teachers,
        "totalStudents": total_students,
        "pendingApprovals": pending_approvals,
        "activeUsers": active_users
    }


# Recent Activity Endpoint
@admin_router.get("/recent-activity")
async def get_recent_activity(
    _admin: User = Depends(get_admin_user),
):
    """Get recent activity for admin dashboard."""
    # For now, return mock data since we don't have a history table implemented
    # In a real implementation, this would query a history/audit table
    from datetime import datetime, timedelta

    # Mock recent activity data
    mock_activities = [
        {
            "id": 1,
            "type": "teacher_added",
            "description": "New teacher John Doe added to Mathematics department",
            "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "userName": "Admin User"
        },
        {
            "id": 2,
            "type": "student_added",
            "description": "New student Jane Smith registered with registration number STU001",
            "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "userName": "Admin User"
        },
        {
            "id": 3,
            "type": "user_approved",
            "description": "Teacher Robert Johnson approved for Physics department",
            "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "userName": "Admin User"
        }
    ]

    return mock_activities
