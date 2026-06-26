from beanie import Document
from typing import Optional
from app.database import get_next_sequence


class Student(Document):
    int_id: int = 0
    course_id: int = 0
    name: Optional[str] = None
    registration_number: Optional[str] = None
    email: Optional[str] = None
    student_class: Optional[str] = None
    department: Optional[str] = None
    attendance: int = 0
    avg_score: int = 0

    class Settings:
        name = "students"
        indexes = [
            [("email", 1), ("course_id", 1)],
            [("registration_number", 1), ("course_id", 1)]
        ]

    async def assign_id(self):
        if self.int_id == 0:
            self.int_id = await get_next_sequence("students")