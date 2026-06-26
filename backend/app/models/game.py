from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.database import get_next_sequence


class GamePlayer(BaseModel):
    """Embedded sub-document — bounded (≤50 players per game)."""
    int_id: int = 0
    student_id: Optional[str] = None
    name: Optional[str] = None
    join_order: int = 0
    score: float = 0.0
    words_submitted: int = 0
    words_valid: int = 0
    status: str = "active"


class GameWord(BaseModel):
    """Embedded sub-document for game words."""
    int_id: int = 0
    word: Optional[str] = None
    submitted_by: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    is_valid: bool = True
    position: int = 0
    validation_reason: Optional[str] = None


class GameQuestion(BaseModel):
    """Embedded sub-document for multiple questions."""
    int_id: int = 0
    question_text: str
    order: int = 0


class ChainAnswerGame(Document):
    int_id: int = 0
    session_id: Optional[str] = None
    teacher_id: Optional[int] = None
    name: str = "New Game"
    chain_variation: str = "standard"
    category: Optional[str] = None
    difficulty_level: str = "medium"
    language: str = "en"
    subject: Optional[str] = None
    status: str = "setup"
    starting_word: str = "Apple"
    time_per_turn: int = 30
    max_words: Optional[int] = None
    ai_suggestions: Optional[str] = None
    penalty_on_invalid: bool = False
    penalty_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    players: List[GamePlayer] = []
    words: List[GameWord] = []
    questions: List[GameQuestion] = []
    current_question_index: int = 0

    class Settings:
        name = "chain_answer_games"

    async def assign_id(self):
        if self.int_id == 0:
            self.int_id = await get_next_sequence("chain_answer_games")


class WordCloudSubmission(BaseModel):
    """Embedded sub-document for word cloud submissions."""
    int_id: int = 0
    word: Optional[str] = None
    submitted_by: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class WordCloudSession(Document):
    int_id: int = 0
    pin: Optional[str] = None
    teacher_id: Optional[int] = None
    prompt: Optional[str] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    submissions: List[WordCloudSubmission] = []

    class Settings:
        name = "word_cloud_sessions"

    async def assign_id(self):
        if self.int_id == 0:
            self.int_id = await get_next_sequence("word_cloud_sessions")
