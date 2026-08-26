from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime
from app.database import get_next_sequence


class CalendarEvent(Document):
    int_id: int = 0
    title: str = ""
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_type: str = "custom"
    color: str = "#264796"
    location: Optional[str] = None
    is_all_day: bool = False
    recurrence: Optional[str] = None
    teacher_name: Optional[str] = None
    student_email: Optional[str] = None
    course_id: Optional[int] = None
    google_event_id: Optional[str] = None
    google_calendar_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "calendar_events"

    async def assign_id(self):
        if self.int_id == 0:
            self.int_id = await get_next_sequence("calendar_events")
