from beanie import Document
from typing import Optional
from app.database import get_next_sequence


class Announcement(Document):
    int_id: int = 0
    course_id: int = 0
    title: Optional[str] = None
    body: Optional[str] = None
    time: Optional[str] = None
    pinned: bool = False
    attachment_path: Optional[str] = None
    created_at: str = ""  # We'll use ISO format string for easy serialization

    class Settings:
        name = "announcements"

    async def assign_id(self):
        if self.int_id == 0:
            self.int_id = await get_next_sequence("announcements")
