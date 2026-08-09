from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime
from app.database import get_next_sequence
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"

class UserStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"

class User(Document):
    int_id: int = 0
    auth_user_id: Optional[str] = None  # Supabase auth.users.id when Supabase Auth is enabled
    name: Optional[str] = None
    email: str
    hashed_password: Optional[str] = None  # Nullable for Google OAuth users
    role: Optional[str] = None  # Storing as string for simplicity
    status: str = UserStatus.APPROVED  # Default APPROVED for backward compat
    google_id: Optional[str] = None
    picture: Optional[str] = None  # Profile picture URL from Google
    employee_id: Optional[str] = None
    registration_number: Optional[str] = None
    department: Optional[str] = None
    last_active: Optional[datetime] = None

    class Settings:
        name = "users"

    async def assign_id(self):
        if self.int_id == 0:
            self.int_id = await get_next_sequence("users")
