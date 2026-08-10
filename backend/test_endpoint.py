#!/usr/bin/env python3
"""
Test the Ollama status endpoint from backend
"""
import httpx
import sys


def test_endpoint():
    """Test /games/chain-answer/status/ollama endpoint"""

    endpoints_to_try = [
        "http://localhost:8000/games/chain-answer/status/ollama",
        "http://127.0.0.1:8000/games/chain-answer/status/ollama",
    ]

    print("=" * 60)
    print("Testing Ollama Status Endpoint")
    print("=" * 60 + "\n")

    for url in endpoints_to_try:
        print(f" Testing: {url}")
        try:
            response = httpx.get(url, timeout=5.0)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"    Endpoint works!")
                print(f"   Ollama Available: {data.get('ollama_available')}")
                print(f"   Endpoint: {data.get('endpoint')}")
                print(f"   Models: {data.get('available_models', [])}")
                return 0
            elif response.status_code == 404:
                print(f"    Endpoint not found (404)")
                print(f"   Response: {response.text[:200]}")
            else:
                print(f"   ️  Unexpected status")
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"    Error: {e}")
        print()

    print("=" * 60)
    print(" Could not reach endpoint")
    print("\nTroubleshooting:")
    print("1. Is backend running? python -m uvicorn app.main:app --reload")
    print("2. Check backend logs for errors")
    print("3. Verify routes are registered: app.include_router(game_routes.router)")
    return 1


if __name__ == "__main__":
    sys.exit(test_endpoint())
