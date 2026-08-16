from dotenv import load_dotenv
from contextlib import asynccontextmanager
from app.services.groq_service import GroqService
from app.routes import course_routes, announcement_routes, resource_routes, student_routes, assignment_routes, submission_routes, appointment_routes, exam_routes, game_routes, websocket_routes, lesson_routes, engagement_routes, analytics_routes, calendar_routes, mail_routes, quiz_routes, omr_routes, wordcloud_routes, report_routes, slido_routes, history_routes, dashboard_routes, trello_routes, google_auth_routes, admin_routes
from fastapi import FastAPI
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
app.include_router(student_routes.student_router)
app.include_router(assignment_routes.assignment_router)
app.include_router(submission_routes.submission_router)
app.include_router(appointment_routes.appointment_router)
app.include_router(exam_routes.exam_router)
app.include_router(game_routes.game_router)
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


@app.get("/")
def root():
    return {"message": "EduAI Backend Running"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "main_api"}


@app.post("/api/auth/login")
def login():
    return {"token": "mock-jwt-token"}


@app.post("/api/ai/evaluate")
def evaluate_answers():
    return {"ai_score": 85.5, "confidence": 0.9}


@app.get("/api/risk/classroom/{classroom_id}")
def get_risk_score(classroom_id: str):
    return {"students_at_risk": 3}
