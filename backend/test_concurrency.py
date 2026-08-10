#!/usr/bin/env python3
"""
EduSlido Concurrency Testing
Tests the Slido platform with classroom-scale concurrent users (30-50 students)
Validates WebSocket performance, poll voting, Q&A interactions, and API responses
"""

import asyncio
import aiohttp
import json
import random
import time
from datetime import datetime
from typing import List, Dict, Any
import statistics


class StudentSimulator:
    """Simulates a student participating in a Slido session"""

    def __init__(self, student_id: int, session_pin: str, base_url: str = "http://localhost:8000"):
        self.student_id = student_id
        self.session_pin = session_pin
        self.base_url = base_url
        self.ws = None
        self.connected = False
        self.metrics = {
            'messages_received': 0,
            'messages_sent': 0,
            'votes_cast': 0,
            'questions_asked': 0,
            'questions_upvoted': 0,
            'errors': 0,
            'response_times': []
        }

    async def connect_websocket(self):
        """Connect to WebSocket and join the session"""
        try:
            ws_url = f"ws://localhost:8000/ws/slido/{self.session_pin}?user_type=student&user_id={self.student_id}"
            session = aiohttp.ClientSession()
            self.ws = await session.ws_connect(ws_url)
            self.connected = True
            print(f"[Student {self.student_id}] Connected to WebSocket")
            return True
        except Exception as e:
            print(f"[Student {self.student_id}] Failed to connect: {e}")
            self.metrics['errors'] += 1
            return False

    async def listen_for_events(self):
        """Listen for incoming WebSocket events"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self.metrics['messages_received'] += 1
                    event = json.loads(msg.data)
                    await self.handle_event(event)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    self.connected = False
                    break
        except Exception as e:
            print(f"[Student {self.student_id}] Listen error: {e}")
            self.metrics['errors'] += 1

    async def handle_event(self, event: Dict[str, Any]):
        """Handle incoming event"""
        event_type = event.get('type')

        if event_type == 'poll_launched':
            await asyncio.sleep(random.uniform(0.1, 0.5))
            await self.vote_on_poll(event.get('poll', {}).get('id'))

        elif event_type == 'qna_question_asked':
            if random.random() < 0.3:
                await self.upvote_question(event.get('question', {}).get('id'))

    async def vote_on_poll(self, poll_id: int):
        """Cast a vote on a poll"""
        try:
            if not self.connected or not self.ws:
                return

            options = ['Option A', 'Option B', 'Option C', 'Option D']
            selected = random.choice(options)

            message = {
                'type': 'poll_vote',
                'poll_id': poll_id,
                'option_text': selected
            }

            start_time = time.time()
            await self.ws.send_str(json.dumps(message))
            response_time = (time.time() - start_time) * 1000

            self.metrics['votes_cast'] += 1
            self.metrics['messages_sent'] += 1
            self.metrics['response_times'].append(response_time)

        except Exception as e:
            self.metrics['errors'] += 1

    async def ask_question(self, question_text: str):
        """Ask a question in Q&A"""
        try:
            if not self.connected or not self.ws:
                return

            message = {
                'type': 'qna_question_asked',
                'question_text': question_text,
                'is_anonymous': random.choice([True, False])
            }

            start_time = time.time()
            await self.ws.send_str(json.dumps(message))
            response_time = (time.time() - start_time) * 1000

            self.metrics['questions_asked'] += 1
            self.metrics['messages_sent'] += 1
            self.metrics['response_times'].append(response_time)

        except Exception as e:
            self.metrics['errors'] += 1

    async def upvote_question(self, question_id: int):
        """Upvote a question"""
        try:
            if not self.connected or not self.ws:
                return

            message = {
                'type': 'qna_upvote',
                'question_id': question_id
            }

            start_time = time.time()
            await self.ws.send_str(json.dumps(message))
            response_time = (time.time() - start_time) * 1000

            self.metrics['questions_upvoted'] += 1
            self.metrics['messages_sent'] += 1
            self.metrics['response_times'].append(response_time)

        except Exception as e:
            self.metrics['errors'] += 1

    async def simulate_participation(self, duration: int = 60):
        """Simulate student participation for specified duration"""
        start_time = time.time()

        questions = [
            "Can you explain that concept again?",
            "What's the deadline for submission?",
            "How does this relate to the previous topic?",
            "Can you provide more examples?",
            "Is this going to be on the exam?"
        ]

        while time.time() - start_time < duration and self.connected:
            if random.random() < 0.2:
                await self.ask_question(random.choice(questions))

            await asyncio.sleep(random.uniform(2, 8))

    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.ws:
            await self.ws.close()
        self.connected = False


class TeacherSimulator:
    """Simulates a teacher running a Slido session"""

    def __init__(self, teacher_id: int, base_url: str = "http://localhost:8000"):
        self.teacher_id = teacher_id
        self.base_url = base_url
        self.session_pin = None
        self.session_id = None
        self.metrics = {'errors': 0, 'polls_created': 0}

    async def start_session(self):
        """Start a new Slido session"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/slido/sessions",
                    json={"assignment_id": 1, "submission_id": None},
                    params={"teacher_id": self.teacher_id}
                ) as response:
                    data = await response.json()
                    self.session_id = data.get('id')
                    self.session_pin = data.get('pin')
                    print(f"[Teacher] Started session PIN {self.session_pin}")
                    return True
        except Exception as e:
            print(f"[Teacher] Failed to start session: {e}")
            self.metrics['errors'] += 1
            return False

    async def launch_poll(self, poll_question: str):
        """Launch a poll"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/slido/sessions/{self.session_id}/polls",
                    json={"question": poll_question,
                          "poll_type": "multiple_choice"},
                    params={"teacher_id": self.teacher_id}
                ) as response:
                    self.metrics['polls_created'] += 1
                    print(f"[Teacher] Launched poll: {poll_question}")
        except Exception as e:
            print(f"[Teacher] Poll error: {e}")
            self.metrics['errors'] += 1

    async def close_session(self):
        """Close the session"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/slido/sessions/{self.session_id}/end"
                ) as response:
                    print(f"[Teacher] Closed session")
                    return True
        except Exception as e:
            print(f"[Teacher] Close error: {e}")
            return False


async def run_concurrency_test(num_students: int = 50, duration: int = 120):
    """Run concurrency test"""
    print(f"\n{'='*60}")
    print(f"EduSlido Concurrency Test - {num_students} Students")
    print(f"{'='*60}\n")

    teacher = TeacherSimulator(teacher_id=1)
    if not await teacher.start_session():
        return

    students = [
        StudentSimulator(student_id=i, session_pin=teacher.session_pin)
        for i in range(1, num_students + 1)
    ]

    print(f"Connecting {num_students} students...")
    connect_results = await asyncio.gather(*[s.connect_websocket() for s in students], return_exceptions=True)
    connected = sum(1 for r in connect_results if r is True)
    print(f"Connected: {connected}/{num_students}\n")

    listen_tasks = [s.listen_for_events() for s in students]
    simulate_tasks = [s.simulate_participation(
        duration=duration) for s in students]

    async def teacher_activities():
        for i in range(duration // 30):
            await asyncio.sleep(30)
            await teacher.launch_poll(f"Poll {i+1}: What do you think?")

    all_tasks = listen_tasks + simulate_tasks + [teacher_activities()]

    await asyncio.gather(*all_tasks, return_exceptions=True)
    await teacher.close_session()
    await asyncio.gather(*[s.disconnect() for s in students])

    # Results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}\n")

    total_messages = sum(s.metrics['messages_sent'] for s in students)
    total_votes = sum(s.metrics['votes_cast'] for s in students)
    total_questions = sum(s.metrics['questions_asked'] for s in students)
    total_errors = sum(s.metrics['errors'] for s in students)

    all_response_times = []
    for s in students:
        all_response_times.extend(s.metrics['response_times'])

    print(f"Connected Students: {connected}/{num_students}")
    print(f"Messages Sent: {total_messages}")
    print(f"Votes Cast: {total_votes}")
    print(f"Questions Asked: {total_questions}")
    print(f"Errors: {total_errors}")
    print(f"Polls Created: {teacher.metrics['polls_created']}")

    if all_response_times:
        print(f"\nResponse Times (ms):")
        print(f"  Min: {min(all_response_times):.2f}")
        print(f"  Avg: {statistics.mean(all_response_times):.2f}")
        print(f"  Max: {max(all_response_times):.2f}")

    status = " PASS" if total_errors == 0 and connected == num_students else " FAIL"
    print(f"\n{status}\n")


if __name__ == "__main__":
    asyncio.run(run_concurrency_test(num_students=50, duration=120))
