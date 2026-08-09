#!/usr/bin/env python3
"""
Test script to verify Chain Answer Game backend with real student data.
Run this after starting the backend server.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_get_active_students():
    """Test fetching active students"""
    print("\n=== Testing GET /students/{course_id}/active ===")
    response = requests.get(f"{BASE_URL}/students/1/active")
    if response.status_code == 200:
        students = response.json()
        print(f" Successfully fetched {len(students)} active students")
        if students:
            print(f"  Sample: {students[0]['name']} (ID: {students[0]['id']})")
        return students
    else:
        print(f" Failed: {response.status_code}")
        print(f"  {response.text}")
        return []


def test_create_game_with_real_students(students):
    """Test creating a game with real student IDs"""
    if len(students) < 2:
        print("\n Need at least 2 students to test game creation")
        return None

    print("\n=== Testing POST /games/chain-answer with real students ===")

    # Use first 2 active students
    players = [
        {"student_id": students[0]["id"]},
        {"student_id": students[1]["id"]}
    ]

    game_data = {
        "name": "Test Chain Game",
        "chain_variation": "standard",
        "difficulty_level": "medium",
        "language": "en",
        "starting_word": "Apple",
        "time_per_turn": 30,
        "max_words": None,
        "penalty_on_invalid": False,
        "penalty_type": None,
        "players": players
    }

    response = requests.post(
        f"{BASE_URL}/games/chain-answer",
        json=game_data,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 201:
        game = response.json()
        print(f" Game created successfully")
        print(f"  Session ID: {game['session_id']}")
        print(f"  Players: {len(game['players'])}")
        for player in game['players']:
            print(
                f"    - {player['name']} (Student ID: {player['student_id']})")
        return game
    else:
        print(f" Failed: {response.status_code}")
        print(f"  {response.text}")
        return None


def main():
    print("Chain Answer Game Backend Test Suite")
    print("=" * 50)

    # Test 1: Get active students
    students = test_get_active_students()

    # Test 2: Create game with real students
    if students and len(students) >= 2:
        game = test_create_game_with_real_students(students)
        if game:
            print("\n All tests passed!")
        else:
            print("\n Game creation test failed")
    else:
        print("\n Skipping game creation test (need at least 2 active students)")

    print("\n" + "=" * 50)
    print("Test complete. Check output above for any failures.")


if __name__ == "__main__":
    main()
