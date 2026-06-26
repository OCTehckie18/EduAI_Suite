from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Query
from app.models.game import ChainAnswerGame, GamePlayer, GameWord, WordCloudSession, WordCloudSubmission
from app.models.quiz import Quiz, QuizSession, QuizPlayer, QuizAnswer
from app.models.slido import SlidoSession, SlidoPoll, PollResponse, SlidoQnA, QnAUpvote
import json
import random
from typing import Dict, Set
from datetime import datetime

# Store active WebSocket connections per game session
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, game_session_id: str, websocket: WebSocket):
        await websocket.accept()
        if game_session_id not in self.active_connections:
            self.active_connections[game_session_id] = set()
        self.active_connections[game_session_id].add(websocket)

    def disconnect(self, game_session_id: str, websocket: WebSocket):
        if game_session_id in self.active_connections:
            self.active_connections[game_session_id].discard(websocket)
            if not self.active_connections[game_session_id]:
                del self.active_connections[game_session_id]

    async def broadcast(self, game_session_id: str, message: dict):
        if game_session_id in self.active_connections:
            for connection in list(self.active_connections[game_session_id]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending message: {e}")
                    self.disconnect(game_session_id, connection)


manager = ConnectionManager()
ws_router = APIRouter()


@ws_router.websocket("/ws/quiz/{pin}")
async def quiz_websocket_endpoint(
    websocket: WebSocket,
    pin: str,
    user_type: str = Query("student"),
    nickname: str = Query(None)
):
    await manager.connect(pin, websocket)

    try:
        session = await QuizSession.find_one(QuizSession.pin == pin)
        if not session:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close()
            return

        quiz = await Quiz.find_one(Quiz.int_id == session.quiz_id)

        player = None
        if user_type == "student" and nickname:
            player = await QuizPlayer.find_one(
                QuizPlayer.session_id == session.int_id,
                QuizPlayer.nickname == nickname
            )

            if not player:
                emojis = ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🐔", "🐧", "🐦", "🐤", "🦆", "🦅", "🦉", "🦇", "🐺", "🐗", "🐴", "🦄", "🐝", "🐛", "🦋", "🐌", "🐞", "🐜", "🦗", "🕷", "🦂", "🐢", "🐍", "🦎", "🦖", "🦕", "🐙", "🦑", "🦐", "🦀", "🐡", "🐠", "🐟", "🐬", "🐳", "🐋", "🦈", "🐊", "🐅", "🐆", "🦓", "🦍", "🦧", "🐘", "🦛", "🦏", "🐪", "🐫", "🦒", "🦘", "🐃", "🐂", "🐄", "🐎", "🐖", "🐏", "🐑", "🐐", "🦌", "🐕", "🐩", "🐈", "🐓", "🦃", "🦚", "🦜", "🦢", "🕊", "🐇", "🦝", "🦡", "🐁", "🐀", "🐿", "🦔"]
                avatar = random.choice(emojis)
                player = QuizPlayer(session_id=session.int_id, nickname=nickname, avatar=avatar)
                await player.assign_id()
                await player.insert()

            all_players = await QuizPlayer.find(QuizPlayer.session_id == session.int_id).to_list()
            players_list = [{"id": p.int_id, "nickname": p.nickname, "avatar": p.avatar} for p in all_players]
            await manager.broadcast(pin, {
                "type": "lobby_update",
                "players": players_list
            })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "start_game":
                if user_type == "teacher":
                    session = await QuizSession.find_one(QuizSession.pin == pin)
                    session.status = "active"
                    session.current_question_index = 0
                    await session.save()

                    if quiz and quiz.questions:
                        question = sorted(quiz.questions, key=lambda x: x.order)[0]
                        await manager.broadcast(pin, {
                            "type": "new_question",
                            "question": {
                                "id": question.int_id,
                                "text": question.question_text,
                                "type": question.question_type,
                                "time_limit": question.time_limit,
                                "image_url": question.image_url,
                                "options": [{"id": o.int_id, "text": o.option_text, "color": o.color} for o in question.options]
                            },
                            "index": 0,
                            "total": len(quiz.questions)
                        })

            elif message["type"] == "submit_answer":
                if user_type == "student" and player:
                    question_id = message.get("question_id")
                    option_id = message.get("option_id")
                    response_time = message.get("response_time", 0)

                    # Refresh player
                    player = await QuizPlayer.find_one(QuizPlayer.int_id == player.int_id)
                    
                    question = None
                    option = None
                    if quiz:
                        for q in quiz.questions:
                            if q.int_id == question_id:
                                question = q
                                for o in q.options:
                                    if o.int_id == option_id:
                                        option = o
                                        break
                                break

                    is_correct = option.is_correct if option else False

                    points = 0
                    if is_correct:
                        time_limit_ms = (question.time_limit * 1000) if question else 20000
                        if response_time <= time_limit_ms:
                            speed_bonus = 1 - ((response_time / time_limit_ms) / 2)
                            points = int(1000 * speed_bonus)
                        player.score += points
                        player.streak += 1
                    else:
                        player.streak = 0

                    await player.save()

                    ans = QuizAnswer(
                        player_id=player.int_id,
                        question_id=question_id,
                        option_id=option_id,
                        is_correct=is_correct,
                        points_earned=points,
                        response_time_ms=response_time
                    )
                    await ans.assign_id()
                    await ans.insert()

                    await websocket.send_json({
                        "type": "answer_submitted",
                        "is_correct": is_correct,
                        "points": points
                    })

                    ans_count = await QuizAnswer.find(QuizAnswer.question_id == question_id).count()
                    await manager.broadcast(pin, {
                        "type": "answer_count_update",
                        "count": ans_count
                    })

            elif message["type"] == "time_up":
                if user_type == "teacher":
                    question_id = message.get("question_id")
                    stats = {}
                    answers = await QuizAnswer.find(QuizAnswer.question_id == question_id).to_list()
                    for a in answers:
                        if a.option_id:
                            stats[a.option_id] = stats.get(a.option_id, 0) + 1

                    question = None
                    if quiz:
                        for q in quiz.questions:
                            if q.int_id == question_id:
                                question = q
                                break

                    correct_option_ids = [o.int_id for o in question.options if o.is_correct] if question else []

                    await manager.broadcast(pin, {
                        "type": "show_results",
                        "stats": stats,
                        "correct_option_ids": correct_option_ids
                    })

            elif message["type"] == "next_question":
                if user_type == "teacher":
                    session = await QuizSession.find_one(QuizSession.pin == pin)
                    session.current_question_index += 1
                    await session.save()
                    
                    if quiz and session.current_question_index < len(quiz.questions):
                        question = sorted(quiz.questions, key=lambda x: x.order)[session.current_question_index]
                        await manager.broadcast(pin, {
                            "type": "new_question",
                            "question": {
                                "id": question.int_id,
                                "text": question.question_text,
                                "type": question.question_type,
                                "time_limit": question.time_limit,
                                "image_url": question.image_url,
                                "options": [{"id": o.int_id, "text": o.option_text, "color": o.color} for o in question.options]
                            },
                            "index": session.current_question_index,
                            "total": len(quiz.questions)
                        })
                    else:
                        session.status = "completed"
                        await session.save()
                        all_players = await QuizPlayer.find(QuizPlayer.session_id == session.int_id).to_list()
                        leaderboard = sorted(all_players, key=lambda x: x.score, reverse=True)
                        await manager.broadcast(pin, {
                            "type": "game_over",
                            "leaderboard": [{"nickname": p.nickname, "score": p.score, "avatar": p.avatar, "rank": i + 1} for i, p in enumerate(leaderboard)]
                        })

    except WebSocketDisconnect:
        manager.disconnect(pin, websocket)


@ws_router.websocket("/ws/wordcloud/{pin}")
async def wordcloud_websocket_endpoint(
    websocket: WebSocket,
    pin: str,
    role: str = Query("student"),
    student_name: str = Query(None)
):
    await manager.connect(pin, websocket)

    try:
        session = await WordCloudSession.find_one(WordCloudSession.pin == pin)
        if not session:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close()
            return

        if role == "teacher":
            words_dict = {}
            for sub in session.submissions:
                words_dict[sub.word] = words_dict.get(sub.word, 0) + 1
            words_list = [{"text": k, "value": v} for k, v in words_dict.items()]
            await websocket.send_json({
                "type": "cloud_update",
                "words": words_list
            })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "submit_word" and role == "student":
                word = message.get("word", "").strip().lower()
                if word:
                    session = await WordCloudSession.find_one(WordCloudSession.pin == pin)
                    submission = WordCloudSubmission(word=word, submitted_by=student_name)
                    session.submissions.append(submission)
                    await session.save()

                    words_dict = {}
                    for sub in session.submissions:
                        words_dict[sub.word] = words_dict.get(sub.word, 0) + 1
                    words_list = [{"text": k, "value": v} for k, v in words_dict.items()]

                    await manager.broadcast(pin, {
                        "type": "cloud_update",
                        "words": words_list
                    })
                    await websocket.send_json({"type": "word_submitted", "word": word})

            elif message["type"] == "end_session" and role == "teacher":
                session = await WordCloudSession.find_one(WordCloudSession.pin == pin)
                session.status = "completed"
                await session.save()
                await manager.broadcast(pin, {
                    "type": "session_ended"
                })

    except WebSocketDisconnect:
        manager.disconnect(pin, websocket)


@ws_router.websocket("/ws/games/chain-answer/{session_id}")
async def chain_answer_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_type: str = Query("student"),
):
    await manager.connect(session_id, websocket)

    try:
        game = await ChainAnswerGame.find_one(ChainAnswerGame.session_id == session_id)
        if not game:
            await websocket.send_json({"type": "error", "message": "Game session not found"})
            await websocket.close()
            return

        players_list = []
        for p in sorted(game.players, key=lambda x: x.join_order):
            players_list.append({
                "id": p.int_id,
                "student_id": p.student_id,
                "name": p.name,
                "join_order": p.join_order,
                "score": p.score,
                "words_submitted": p.words_submitted,
                "words_valid": p.words_valid,
                "status": p.status,
            })

        chain = []
        for w in sorted(game.words, key=lambda x: x.position):
            chain.append({
                "id": w.int_id,
                "word": w.word,
                "submitted_by": w.submitted_by,
                "is_valid": w.is_valid,
                "position": w.position,
            })

        current_player_index = 0
        if len(chain) > 0 and len(players_list) > 0:
            last_word = chain[-1]
            last_submitter = last_word.get("submitted_by")
            if last_submitter and last_submitter != "system":
                for i, p in enumerate(players_list):
                    if str(p["student_id"]) == str(last_submitter):
                        current_player_index = (i + 1) % len(players_list)
                        break

        await websocket.send_json({
            "type": "initial_state",
            "game": {
                "id": game.int_id,
                "session_id": game.session_id,
                "name": game.name,
                "chain_variation": game.chain_variation,
                "difficulty_level": game.difficulty_level,
                "status": game.status,
                "starting_word": game.starting_word,
                "time_per_turn": game.time_per_turn or 30,
                "questions": [{"id": q.int_id, "question_text": q.question_text, "order": q.order} for q in game.questions],
                "current_question_index": game.current_question_index,
            },
            "players": players_list,
            "chain": chain,
            "currentPlayerIndex": current_player_index,
        })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "join":
                player_id = message.get("player_id")
                player_name = message.get("player_name", "Anonymous")
                game = await ChainAnswerGame.find_one(ChainAnswerGame.session_id == session_id)
                if game:
                    player_exists = any(str(p.student_id) == str(player_id) for p in game.players)
                    if not player_exists and user_type == "student":
                        next_join_order = max((p.join_order for p in game.players), default=0) + 1
                        next_int_id = max((p.int_id for p in game.players), default=0) + 1
                        new_player = GamePlayer(
                            int_id=next_int_id,
                            student_id=str(player_id),
                            name=player_name,
                            join_order=next_join_order,
                            status="active"
                        )
                        game.players.append(new_player)
                        await game.save()

                    updated_players = []
                    for p in sorted(game.players, key=lambda x: x.join_order):
                        updated_players.append({
                            "id": p.int_id,
                            "student_id": p.student_id,
                            "name": p.name,
                            "join_order": p.join_order,
                            "score": p.score,
                            "words_submitted": p.words_submitted,
                            "words_valid": p.words_valid,
                            "status": p.status,
                        })
                    await manager.broadcast(session_id, {
                        "type": "player_joined",
                        "player_id": player_id,
                        "players": updated_players,
                    })

            elif msg_type == "submit_word":
                word_text = message.get("word", "").strip()
                player_id = str(message.get("player_id", ""))

                if not word_text:
                    await websocket.send_json({"type": "error", "message": "Empty word"})
                    continue

                game = await ChainAnswerGame.find_one(ChainAnswerGame.session_id == session_id)
                if not game or game.status != "active":
                    await websocket.send_json({"type": "error", "message": "Game is not active"})
                    continue

                next_position = max((w.position for w in game.words), default=0) + 1

                new_word = GameWord(
                    word=word_text,
                    submitted_by=player_id,
                    is_valid=True,
                    position=next_position,
                )
                game.words.append(new_word)

                player_stats = {}
                for p in game.players:
                    if str(p.student_id) == player_id:
                        p.words_submitted += 1
                        p.words_valid += 1
                        p.score += 10
                        player_stats = {
                            "score": p.score,
                            "words_submitted": p.words_submitted,
                            "words_valid": p.words_valid,
                        }
                        break

                await game.save()

                await manager.broadcast(session_id, {
                    "type": "word_submitted",
                    "word": {
                        "id": new_word.int_id,
                        "word": new_word.word,
                        "submitted_by": new_word.submitted_by,
                        "is_valid": new_word.is_valid,
                        "position": new_word.position,
                    },
                    "player_stats": player_stats,
                })

            elif msg_type in ("start_game", "game_started"):
                if user_type != "teacher":
                    await websocket.send_json({"type": "error", "message": "Only teachers can start games"})
                    continue

                game = await ChainAnswerGame.find_one(ChainAnswerGame.session_id == session_id)
                if game and game.status == "setup":
                    game.status = "active"
                    game.started_at = datetime.utcnow()
                    if game.questions:
                        game.current_question_index = 0
                        game.starting_word = game.questions[0].question_text
                        starting_word_entry = GameWord(
                            int_id=1,
                            word=game.starting_word,
                            submitted_by="system",
                            is_valid=True,
                            position=0
                        )
                        game.words = [starting_word_entry]
                    await game.save()
                    await manager.broadcast(session_id, {
                        "type": "game_started",
                        "status": "active",
                        "starting_word": game.starting_word,
                        "current_question_index": game.current_question_index,
                    })

            elif msg_type == "next_question":
                if user_type != "teacher":
                    await websocket.send_json({"type": "error", "message": "Only teachers can advance questions"})
                    continue

                game = await ChainAnswerGame.find_one(ChainAnswerGame.session_id == session_id)
                if game and game.status == "active":
                    if game.questions and game.current_question_index + 1 < len(game.questions):
                        game.current_question_index += 1
                        game.starting_word = game.questions[game.current_question_index].question_text
                        
                        starting_word_entry = GameWord(
                            int_id=1,
                            word=game.starting_word,
                            submitted_by="system",
                            is_valid=True,
                            position=0
                        )
                        game.words = [starting_word_entry]
                        await game.save()
                        
                        await manager.broadcast(session_id, {
                            "type": "new_question",
                            "current_question_index": game.current_question_index,
                            "starting_word": game.starting_word,
                        })
                    else:
                        game.status = "completed"
                        game.ended_at = datetime.utcnow()
                        await game.save()
                        await manager.broadcast(session_id, {
                            "type": "game_ended",
                            "status": "completed",
                        })

            elif msg_type in ("end_game", "game_ended"):
                game = await ChainAnswerGame.find_one(ChainAnswerGame.session_id == session_id)
                if game and game.status != "completed":
                    game.status = "completed"
                    game.ended_at = datetime.utcnow()
                    await game.save()
                    await manager.broadcast(session_id, {
                        "type": "game_ended",
                        "status": "completed",
                    })

            elif msg_type == "skip_turn":
                skipped_player_id = str(message.get("player_id", ""))
                game = await ChainAnswerGame.find_one(ChainAnswerGame.session_id == session_id)
                if game and game.status == "active":
                    players = sorted(game.players, key=lambda x: x.join_order)
                    next_index = 0
                    for i, p in enumerate(players):
                        if str(p.student_id) == skipped_player_id:
                            next_index = (i + 1) % len(players)
                            break
                    await manager.broadcast(session_id, {
                        "type": "turn_skipped",
                        "skipped_player_id": skipped_player_id,
                        "next_player_index": next_index,
                        "time_per_turn": game.time_per_turn or 30,
                    })

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)


@ws_router.websocket("/ws/slido/{pin}")
async def slido_websocket_endpoint(
    websocket: WebSocket,
    pin: str,
    user_type: str = Query("student"),
    user_id: int = Query(None)
):
    await manager.connect(pin, websocket)

    try:
        session = await SlidoSession.find_one(SlidoSession.pin == pin)
        if not session:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close()
            return

        await websocket.send_json({
            "type": "session_state",
            "session_id": session.int_id,
            "status": session.status,
            "active_view": session.active_view,
            "current_slide": session.current_slide,
            "user_type": user_type
        })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "poll_launched" and user_type in ("teacher", "presenter"):
                poll_id = message.get("poll_id")
                poll = await SlidoPoll.find_one(SlidoPoll.int_id == poll_id)
                if poll:
                    poll.is_active = True
                    await poll.save()
                    await manager.broadcast(pin, {
                        "type": "poll_launched",
                        "poll": {
                            "id": poll.int_id,
                            "question": poll.question,
                            "poll_type": poll.poll_type,
                            "is_active": True
                        }
                    })
                    session = await SlidoSession.find_one(SlidoSession.pin == pin)
                    session.active_view = "poll"
                    session.updated_at = datetime.utcnow()
                    await session.save()

            elif message_type == "poll_closed" and user_type in ("teacher", "presenter"):
                poll_id = message.get("poll_id")
                poll = await SlidoPoll.find_one(SlidoPoll.int_id == poll_id)
                if poll:
                    poll.is_active = False
                    await poll.save()
                    
                    responses = await PollResponse.find(PollResponse.poll_id == poll_id).to_list()
                    results = {}
                    
                    if poll.poll_type == "multiple_choice":
                        for resp in responses:
                            if resp.option_text:
                                results[resp.option_text] = results.get(resp.option_text, 0) + 1
                    elif poll.poll_type == "rating":
                        rating_counts = {}
                        for resp in responses:
                            if resp.response_value is not None:
                                rating_counts[resp.response_value] = rating_counts.get(resp.response_value, 0) + 1
                        results = {"ratings": rating_counts}
                    
                    await manager.broadcast(pin, {
                        "type": "poll_results",
                        "poll_id": poll_id,
                        "results": results,
                        "total_responses": poll.total_responses
                    })

            elif message_type == "presentation_state_changed" and user_type in ("teacher", "presenter"):
                active_view = message.get("active_view")
                current_slide = message.get("current_slide")
                session = await SlidoSession.find_one(SlidoSession.pin == pin)
                
                if active_view:
                    session.active_view = active_view
                if current_slide is not None:
                    session.current_slide = current_slide
                
                session.updated_at = datetime.utcnow()
                await session.save()
                
                await manager.broadcast(pin, {
                    "type": "presentation_state_changed",
                    "active_view": session.active_view,
                    "current_slide": session.current_slide
                })

            elif message_type == "qna_answered" and user_type in ("teacher", "presenter"):
                question_id = message.get("question_id")
                answer_text = message.get("answer_text")
                question = await SlidoQnA.find_one(SlidoQnA.int_id == question_id)
                if question:
                    question.is_answered = True
                    question.teacher_answer = answer_text
                    question.answered_at = datetime.utcnow()
                    question.updated_at = datetime.utcnow()
                    await question.save()
                    await manager.broadcast(pin, {
                        "type": "qna_answered",
                        "question_id": question_id,
                        "answer": answer_text,
                        "answered_at": question.answered_at.isoformat() if question.answered_at else None
                    })

            elif message_type == "poll_vote" and user_type == "student":
                poll_id = message.get("poll_id")
                option_text = message.get("option_text")
                response_text = message.get("response_text")
                response_value = message.get("response_value")
                
                poll = await SlidoPoll.find_one(SlidoPoll.int_id == poll_id)
                if poll and poll.is_active:
                    poll_response = PollResponse(
                        poll_id=poll_id,
                        student_id=user_id,
                        option_text=option_text,
                        response_text=response_text,
                        response_value=response_value
                    )
                    await poll_response.assign_id()
                    await poll_response.insert()
                    poll.total_responses += 1
                    await poll.save()
                    
                    await websocket.send_json({
                        "type": "poll_vote_submitted",
                        "poll_id": poll_id,
                        "success": True
                    })
                    await manager.broadcast(pin, {
                        "type": "poll_response_count_update",
                        "poll_id": poll_id,
                        "total_responses": poll.total_responses
                    })

            elif message_type == "qna_question_asked" and user_type == "student":
                question_text = message.get("question_text")
                is_anonymous = message.get("is_anonymous", False)
                session = await SlidoSession.find_one(SlidoSession.pin == pin)
                question = SlidoQnA(
                    session_id=session.int_id,
                    student_id=user_id,
                    question_text=question_text,
                    is_anonymous=is_anonymous
                )
                await question.assign_id()
                await question.insert()
                
                await manager.broadcast(pin, {
                    "type": "qna_question_asked",
                    "question": {
                        "id": question.int_id,
                        "question_text": question.question_text,
                        "is_anonymous": question.is_anonymous,
                        "upvotes": question.upvotes,
                        "is_answered": question.is_answered,
                        "created_at": question.created_at.isoformat() if question.created_at else None
                    }
                })

            elif message_type == "qna_upvote" and user_type == "student":
                question_id = message.get("question_id")
                question = await SlidoQnA.find_one(SlidoQnA.int_id == question_id)
                if question:
                    existing = await QnAUpvote.find_one(
                        QnAUpvote.question_id == question_id,
                        QnAUpvote.student_id == user_id
                    )
                    if not existing:
                        upvote = QnAUpvote(question_id=question_id, student_id=user_id)
                        await upvote.assign_id()
                        await upvote.insert()
                        question.upvotes += 1
                        question.updated_at = datetime.utcnow()
                        await question.save()
                        
                        await manager.broadcast(pin, {
                            "type": "qna_upvote_updated",
                            "question_id": question_id,
                            "upvotes": question.upvotes
                        })

            elif message_type == "end_session" and user_type == "teacher":
                session = await SlidoSession.find_one(SlidoSession.pin == pin)
                session.status = "ended"
                session.ended_at = datetime.utcnow()
                await session.save()
                await manager.broadcast(pin, {
                    "type": "session_ended",
                    "session_id": session.int_id,
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None
                })

    except WebSocketDisconnect:
        manager.disconnect(pin, websocket)
