import asyncio
import os
from dotenv import load_dotenv
from app.database import init_db

load_dotenv()

async def clear_data():
    print("Initializing Database connection...")
    await init_db()

    # Import all document models
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
    from app.models.trello import TrelloBoard, TrelloColumn, TrelloCard
    from app.models.calendar import CalendarEvent

    models_to_clear = [
        Course, Student, Announcement, Assignment, Submission,
        Appointment, Lesson, Exam,
        Quiz, QuizSession, QuizPlayer, QuizAnswer,
        ChainAnswerGame, WordCloudSession,
        MailDraft, MailHistory, ActionHistory, Report,
        OMRJob, OMRSubmission,
        PresentationAssignment, PresentationSubmission,
        SlidoSession, SlidoPoll, PollResponse, SlidoQnA,
        QnAUpvote, SubmissionInteraction,
        TrelloBoard, TrelloColumn, TrelloCard,
        CalendarEvent
    ]

    print("\n--- Clearing Test Data ---")
    for model in models_to_clear:
        count = await model.find_all().count()
        print(f"Clearing collection {model.__name__} ({count} documents)...")
        await model.find_all().delete()
        
    print("\n--- Clearing Counters ---")
    # Reset auto-increment counters so sequential IDs start at 1 again
    from app.database import client, DB_NAME
    db = client[DB_NAME]
    await db.counters.delete_many({})
    print("Counters collection cleared.")

    print("\n--- Database Cleaned Successfully! ---")

if __name__ == "__main__":
    asyncio.run(clear_data())
