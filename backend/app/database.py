"""
MongoDB connection layer using Motor (async) + Beanie ODM.
Replaces the previous SQLAlchemy/SQLite setup.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import os
import logging

# Monkeypatch AsyncIOMotorClient to prevent Beanie initialization crash due to missing append_metadata
if not hasattr(AsyncIOMotorClient, "append_metadata"):
    AsyncIOMotorClient.append_metadata = lambda self, *args, **kwargs: None

logger = logging.getLogger(__name__)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "eduai_suite")

client: AsyncIOMotorClient = None


async def get_next_sequence(collection_name: str) -> int:
    """
    Auto-increment integer ID generator.
    Uses a 'counters' collection to maintain sequential IDs per collection,
    preserving the integer-ID API contract the frontend expects.
    """
    db = client[DB_NAME]
    result = await db.counters.find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"]


async def init_db():
    """Initialize MongoDB connection and register all Beanie document models."""
    global client
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]

    # Import all document models
    from app.models.user import User
    from app.models.course import Course
    from app.models.student import Student
    from app.models.announcement import Announcement
    from app.models.assignment import Assignment
    from app.models.submission import Submission
    from app.models.appointment import Appointment
    from app.models.lesson import Lesson
    from app.models.exam import Exam
    from app.models.quiz import Quiz, QuizSession, QuizPlayer, QuizAnswer
    from app.models.game import ChainAnswerGame, WordCloudSession
    from app.models.mail import MailDraft, MailHistory
    from app.models.history import ActionHistory
    from app.models.report import Report
    from app.models.omr import OMRJob, OMRSubmission
    from app.models.slido import (
        PresentationAssignment,
        PresentationSubmission,
        SlidoSession,
        SlidoPoll,
        PollResponse,
        SlidoQnA,
        QnAUpvote,
        SubmissionInteraction,
    )
    from app.models.resource import Resource
    from app.models.trello import TrelloBoard, TrelloColumn, TrelloCard
    from app.models.calendar import CalendarEvent

    await init_beanie(
        database=db,
        document_models=[
            User, Course, Student, Announcement, Assignment, Submission,
            Appointment, Lesson, Exam,
            Quiz, QuizSession, QuizPlayer, QuizAnswer,
            ChainAnswerGame, WordCloudSession,
            MailDraft, MailHistory, ActionHistory, Report,
            OMRJob, OMRSubmission,
            PresentationAssignment, PresentationSubmission,
            SlidoSession, SlidoPoll, PollResponse, SlidoQnA,
            QnAUpvote, SubmissionInteraction,
            TrelloBoard, TrelloColumn, TrelloCard,
            CalendarEvent, Resource,
        ],
    )
    logger.info(f"✅ MongoDB connected: {MONGODB_URL}/{DB_NAME}")


async def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")