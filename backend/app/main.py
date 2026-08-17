from dotenv import load_dotenv
from contextlib import asynccontextmanager
from app.services.groq_service import GroqService, DEFAULT_MODEL
from app.routes import course_routes, announcement_routes, resource_routes, student_routes, assignment_routes, submission_routes, appointment_routes, exam_routes, game_routes, websocket_routes, lesson_routes, engagement_routes, analytics_routes, calendar_routes, mail_routes, quiz_routes, omr_routes, wordcloud_routes, report_routes, slido_routes, history_routes, dashboard_routes, trello_routes, google_auth_routes, admin_routes
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Any
from app.database import init_db
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# Load environment variables FIRST
load_dotenv()

uploads_dir = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "uploads"))
os.makedirs(uploads_dir, exist_ok=True)

local_uploads_dir = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "local_uploads"))
os.makedirs(local_uploads_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Initialize Groq service on startup
    GroqService.initialize()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/local_uploads", StaticFiles(directory=local_uploads_dir),
          name="local_uploads")

app.include_router(course_routes.course_router)
app.include_router(announcement_routes.announcement_router)
app.include_router(resource_routes.resource_router)
app.include_router(lesson_routes.lesson_router)
app.include_router(engagement_routes.engagement_router)
app.include_router(analytics_routes.analytics_router)
app.include_router(calendar_routes.calendar_router)
app.include_router(mail_routes.mail_router)
app.include_router(quiz_routes.quiz_router)
app.include_router(omr_routes.omr_router)
app.include_router(wordcloud_routes.wordcloud_router)
app.include_router(report_routes.report_router)
app.include_router(slido_routes.slido_router)
app.include_router(history_routes.history_router)
app.include_router(dashboard_routes.dashboard_router)
app.include_router(trello_routes.trello_router)
app.include_router(websocket_routes.ws_router)
app.include_router(google_auth_routes.google_auth_router)
app.include_router(admin_routes.admin_router)


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    history: list[dict[str, Any]] = Field(default_factory=list)


@app.get("/")
def root():
    app.include_router(student_routes.student_router)
    app.include_router(assignment_routes.assignment_router)
    app.include_router(submission_routes.submission_router)
    app.include_router(appointment_routes.appointment_router)
    app.include_router(exam_routes.exam_router)
    app.include_router(game_routes.game_router)
    return {"message": "EduAI Backend Running"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "main_api"}


@app.post("/ai/chat")
def chat(request: AIChatRequest):
    """Generate an AI response without exposing provider credentials to clients."""
    if not GroqService._available or not GroqService._client:
        raise HTTPException(
            status_code=503, detail="AI service is not configured")

    messages = [{
        "role": "system",
        "content": "You are EduAI Assistant. Answer using the institution's academic context when it is provided. Be concise and do not invent student, course, or performance data.",
    }]
    for item in request.history[-10:]:
        if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": request.message})

    try:
        response = GroqService._client.chat.completions.create(
            messages=messages,
            model=DEFAULT_MODEL,
            temperature=0.4,
            max_tokens=1200,
        )
        content = response.choices[0].message.content
        if not content:
            raise HTTPException(
                status_code=502, detail="AI returned an empty response")
        return {"content": content}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"AI request failed: {exc}") from exc
