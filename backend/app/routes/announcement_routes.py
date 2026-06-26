from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from app.models.announcement import Announcement
from app.models.course import Course
from app.schemas.announcement import AnnouncementResponse
from app.utils.file_uploads import save_optional_upload
from typing import Optional

announcement_router = APIRouter(prefix="/announcements", tags=["Announcements"])

@announcement_router.get("/{course_id}", response_model=list[AnnouncementResponse])
async def get_announcements(course_id: int):
    # Sort by pinned (True first), then by created_at descending
    announcements = await Announcement.find(Announcement.course_id == course_id).sort(
        [("pinned", -1), ("created_at", -1)]
    ).to_list()
    return [
        AnnouncementResponse(**{**a.model_dump(), "id": a.int_id}) for a in announcements
    ]

@announcement_router.post("/{course_id}", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    course_id: int,
    title: str = Form(...),
    body: str = Form(...),
    time: str = Form("Just now"),
    pinned: bool = Form(False),
    file: Optional[UploadFile] = File(None)
):
    course = await Course.find_one(Course.int_id == course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    from datetime import datetime
    final_time = time
    if time == "Just now":
        final_time = datetime.now().strftime("%I:%M %p, %d %b")

    new_announcement = Announcement(
        course_id=course_id,
        title=title,
        body=body,
        time=final_time,
        pinned=pinned,
        attachment_path=save_optional_upload(file, "announcements"),
        created_at=datetime.utcnow().isoformat()
    )
    await new_announcement.assign_id()
    await new_announcement.insert()
    
    return AnnouncementResponse(**{**new_announcement.model_dump(), "id": new_announcement.int_id})

@announcement_router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(announcement_id: int):
    announcement = await Announcement.find_one(Announcement.int_id == announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
        
    await announcement.delete()
    return None
