from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Player-related schemas


class GamePlayerCreate(BaseModel):
    student_id: int  # Now uses actual student ID from database


class GamePlayerResponse(BaseModel):
    id: int
    student_id: str
    name: str
    join_order: int
    score: float
    words_submitted: int
    words_valid: int
    status: str

    class Config:
        from_attributes = True

# Word-related schemas


class GameWordCreate(BaseModel):
    word: str
    submitted_by: str
    is_valid: bool = True
    validation_reason: Optional[str] = None


class GameWordResponse(BaseModel):
    id: int
    word: str
    submitted_by: str
    submitted_at: datetime
    is_valid: bool
    position: int
    validation_reason: Optional[str]

    class Config:
        from_attributes = True

# Game question schemas

class GameQuestionCreate(BaseModel):
    question_text: str


class GameQuestionResponse(BaseModel):
    id: int
    question_text: str
    order: int

    class Config:
        from_attributes = True


# Game session schemas


class ChainAnswerGameCreate(BaseModel):
    name: str
    chain_variation: str
    category: Optional[str] = None
    difficulty_level: str
    language: str
    subject: Optional[str] = None
    starting_word: str
    time_per_turn: int = 30
    max_words: Optional[int] = None
    penalty_on_invalid: bool = False
    penalty_type: Optional[str] = None
    players: List[GamePlayerCreate]
    questions: Optional[List[GameQuestionCreate]] = []


class ChainAnswerGameUpdate(BaseModel):
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class ChainAnswerGameResponse(BaseModel):
    id: int
    session_id: str
    name: str
    chain_variation: str
    category: Optional[str]
    difficulty_level: str
    language: str
    subject: Optional[str]
    status: str
    starting_word: str
    time_per_turn: int
    ai_suggestions: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    players: List[GamePlayerResponse]
    words: List[GameWordResponse]
    questions: Optional[List[GameQuestionResponse]] = []
    current_question_index: Optional[int] = 0

    class Config:
        from_attributes = True

# Simplified response for game listing


class ChainAnswerGameListResponse(BaseModel):
    id: int
    session_id: str
    name: str
    difficulty_level: str
    subject: Optional[str]
    status: str
    created_at: datetime
    players: List[GamePlayerResponse]

    class Config:
        from_attributes = True
