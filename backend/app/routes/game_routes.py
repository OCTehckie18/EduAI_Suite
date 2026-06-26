from fastapi import APIRouter, HTTPException, status
from app.models.game import ChainAnswerGame, GamePlayer, GameWord, GameQuestion
from app.models.student import Student
from app.schemas.game import (
    ChainAnswerGameCreate,
    ChainAnswerGameResponse,
    ChainAnswerGameListResponse,
    ChainAnswerGameUpdate,
    GameWordCreate,
    GameWordResponse,
)
from app.services.word_service import WordService
from datetime import datetime
import uuid
import json

game_router = APIRouter(prefix="/games", tags=["Games"])

def format_game_response(game: ChainAnswerGame) -> dict:
    res = game.model_dump()
    res["id"] = game.int_id
    
    res["players"] = []
    for p in game.players:
        d = p.model_dump()
        d["id"] = p.int_id
        res["players"].append(d)
        
    res["words"] = []
    for w in game.words:
        d = w.model_dump()
        d["id"] = w.int_id
        res["words"].append(d)
        
    res["questions"] = []
    for q in game.questions:
        d = q.model_dump()
        d["id"] = q.int_id
        res["questions"].append(d)
        
    return res


@game_router.post("/chain-answer", response_model=ChainAnswerGameResponse, status_code=status.HTTP_201_CREATED)
async def create_chain_answer_game(game_data: ChainAnswerGameCreate):
    """Create a new Chain Answer game session"""
    session_id = f"game_{uuid.uuid4().hex[:8]}"

    word_suggestions = None
    if game_data.subject:
        suggestions = WordService.generate_word_suggestions(
            subject=game_data.subject,
            difficulty=game_data.difficulty_level,
            count=5,
            chain_variation=game_data.chain_variation,
            starting_word=game_data.starting_word
        )
        if suggestions:
            word_suggestions = json.dumps(suggestions)

    players_list = []
    for idx, player_data in enumerate(game_data.players, start=1):
        try:
            sid_int = int(player_data.student_id)
        except:
            sid_int = None
            
        student = None
        if sid_int is not None:
            student = await Student.find_one(Student.int_id == sid_int)

        if not student:
            raise HTTPException(
                status_code=404,
                detail=f"Student with ID {player_data.student_id} not found"
            )

        new_player = GamePlayer(
            int_id=idx,
            student_id=str(student.int_id),
            name=student.name,
            join_order=idx
        )
        players_list.append(new_player)

    questions_list = []
    if game_data.questions:
        for idx, q_data in enumerate(game_data.questions, start=1):
            questions_list.append(
                GameQuestion(
                    int_id=idx,
                    question_text=q_data.question_text,
                    order=idx
                )
            )

    starting_word_entry = GameWord(
        int_id=1,
        word=game_data.starting_word,
        submitted_by="system",
        is_valid=True,
        position=0
    )

    new_game = ChainAnswerGame(
        session_id=session_id,
        name=game_data.name,
        chain_variation=game_data.chain_variation,
        category=game_data.category,
        difficulty_level=game_data.difficulty_level,
        language=game_data.language,
        subject=game_data.subject,
        starting_word=game_data.starting_word,
        time_per_turn=game_data.time_per_turn,
        max_words=game_data.max_words,
        penalty_on_invalid=game_data.penalty_on_invalid,
        penalty_type=game_data.penalty_type,
        ai_suggestions=word_suggestions,
        status="setup",
        players=players_list,
        words=[starting_word_entry],
        questions=questions_list,
        current_question_index=0
    )
    await new_game.assign_id()
    await new_game.insert()

    return format_game_response(new_game)


@game_router.get("/chain-answer", response_model=list[ChainAnswerGameListResponse])
async def get_all_chain_answer_games(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None
):
    """Get all Chain Answer games"""
    query = ChainAnswerGame.find_all()

    if status_filter:
        query = query.find(ChainAnswerGame.status == status_filter)

    games = await query.skip(skip).limit(limit).to_list()
    res = []
    for g in games:
        d = g.model_dump()
        d["id"] = g.int_id
        d["players"] = []
        for p in g.players:
            dp = p.model_dump()
            dp["id"] = p.int_id
            d["players"].append(dp)
        res.append(d)
    return res


@game_router.get("/chain-answer/{game_id}", response_model=ChainAnswerGameResponse)
async def get_chain_answer_game(game_id: int):
    """Get a specific Chain Answer game by ID"""
    game = await ChainAnswerGame.find_one(ChainAnswerGame.int_id == game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )
        
    return format_game_response(game)


@game_router.get("/chain-answer/session/{session_id}", response_model=ChainAnswerGameResponse)
async def get_chain_answer_game_by_session(session_id: str):
    """Get a specific Chain Answer game by session ID"""
    game = await ChainAnswerGame.find_one(ChainAnswerGame.session_id == session_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game session not found"
        )
        
    return format_game_response(game)


@game_router.post("/chain-answer/{game_id}/start", response_model=ChainAnswerGameResponse)
async def start_chain_answer_game(game_id: int):
    """Start a Chain Answer game"""
    game = await ChainAnswerGame.find_one(ChainAnswerGame.int_id == game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    if game.status != "setup":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start game in {game.status} status"
        )

    if len(game.players) < 2:
        raise HTTPException(
            status_code=400,
            detail="Minimum 2 players required to start the game"
        )

    game.status = "active"
    game.started_at = datetime.utcnow()
    await game.save()

    return format_game_response(game)


@game_router.post("/chain-answer/{game_id}/word", response_model=GameWordResponse, status_code=status.HTTP_201_CREATED)
async def submit_word(game_id: int, word_data: GameWordCreate):
    """Submit a word to the game"""
    game = await ChainAnswerGame.find_one(ChainAnswerGame.int_id == game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    if game.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Game is not active"
        )

    # Find the maximum position in the embedded words list
    max_position = max((w.position for w in game.words), default=0)
    next_position = max_position + 1

    # Create new word with sequentially generated int_id
    next_word_id = len(game.words) + 1
    new_word = GameWord(
        int_id=next_word_id,
        word=word_data.word,
        submitted_by=word_data.submitted_by,
        is_valid=word_data.is_valid,
        position=next_position,
        validation_reason=word_data.validation_reason
    )
    game.words.append(new_word)

    # Find and update player stats in the embedded players list
    player = next((p for p in game.players if p.student_id == word_data.submitted_by), None)
    if player:
        player.words_submitted = (player.words_submitted or 0) + 1
        if word_data.is_valid:
            player.words_valid = (player.words_valid or 0) + 1
            player.score = (player.score or 0) + 10

    await game.save()

    res = new_word.model_dump()
    res["id"] = new_word.int_id
    return res


@game_router.post("/chain-answer/{game_id}/end", response_model=ChainAnswerGameResponse)
async def end_chain_answer_game(game_id: int):
    """End a Chain Answer game"""
    game = await ChainAnswerGame.find_one(ChainAnswerGame.int_id == game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    if game.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="Game is already completed"
        )

    game.status = "completed"
    game.ended_at = datetime.utcnow()
    await game.save()

    return format_game_response(game)


@game_router.post("/chain-answer/{game_id}/pause", response_model=ChainAnswerGameResponse)
async def pause_chain_answer_game(game_id: int):
    """Pause a Chain Answer game"""
    game = await ChainAnswerGame.find_one(ChainAnswerGame.int_id == game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    if game.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Only active games can be paused"
        )

    game.status = "paused"
    await game.save()

    return format_game_response(game)


@game_router.post("/chain-answer/{game_id}/resume", response_model=ChainAnswerGameResponse)
async def resume_chain_answer_game(game_id: int):
    """Resume a paused Chain Answer game"""
    game = await ChainAnswerGame.find_one(ChainAnswerGame.int_id == game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    if game.status != "paused":
        raise HTTPException(
            status_code=400,
            detail="Only paused games can be resumed"
        )

    game.status = "active"
    await game.save()

    return format_game_response(game)


@game_router.post("/chain-answer/{game_id}/next-question", response_model=ChainAnswerGameResponse)
async def next_question(game_id: int):
    """Advance to the next question in the game"""
    game = await ChainAnswerGame.find_one(ChainAnswerGame.int_id == game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    if game.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Game is not active"
        )

    if not game.questions or game.current_question_index + 1 >= len(game.questions):
        # End the game if no more questions
        game.status = "completed"
        game.ended_at = datetime.utcnow()
    else:
        game.current_question_index += 1
        game.starting_word = game.questions[game.current_question_index].question_text
        
        # Reset the words array for the new question
        starting_word_entry = GameWord(
            int_id=1,
            word=game.starting_word,
            submitted_by="system",
            is_valid=True,
            position=0
        )
        game.words = [starting_word_entry]

    await game.save()
    return format_game_response(game)


@game_router.get("/chain-answer/status/groq")
async def get_word_engine_status():
    """Check word engine availability — always available (local dictionary)"""
    return {
        "groq_available": True,
        "service": "Local Dictionary Engine (nltk + Word Bank)",
        "message": "Word engine is running — deterministic, no external API required"
    }


@game_router.delete("/chain-answer/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chain_answer_game(game_id: int):
    """Delete a Chain Answer game"""
    game = await ChainAnswerGame.find_one(ChainAnswerGame.int_id == game_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    # Broadcast to all connected clients that the game has ended because it was deleted
    try:
        from app.routes.websocket_routes import manager
        await manager.broadcast(game.session_id, {
            "type": "game_ended",
            "status": "completed",
            "message": "Game session deleted by teacher"
        })
    except Exception as e:
        print(f"Error broadcasting game deletion: {e}")

    await game.delete()
    return None
