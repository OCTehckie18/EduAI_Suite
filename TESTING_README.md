# EduAI Suite - Testing Outcomes and Strategy

This document outlines the testing strategy, setup, and current outcomes for the EduAI Suite monorepo. It serves as a reference for the testing frameworks implemented across the frontend and backend applications on the testing-setup branch.

## 1. Testing Frameworks

### Frontend (Apps: TeacherBuddy, EduGames)
- Runner: Vitest
- Environment: JSDOM
- Libraries: React Testing Library, User Event

### Backend (FastAPI)
- Runner: Pytest
- Async Support: Pytest-Asyncio
- Request Client: HTTPX
- Database Mocking: Real MongoDB Database (Test Database defined by MONGODB_DB)

## 2. Test Installation and Execution

Install backend test dependencies before running the suite:

    python -m pip install -r backend/requirements-test.txt

All tests are orchestrated from the root directory using concurrently.

Command to run all tests:
```bash
npm run test
```
This command triggers the test suites for TeacherBuddy, EduGames, and the Backend simultaneously.

## 3. Current Test Coverage & Outcomes

### Frontend: TeacherBuddy
- Target: src/store/useAuthStore.test.ts
- Scope: Unit tests verifying the initial state, login state updates, and logout state updates within the Zustand authentication store.
- Status: PASS

### Frontend: EduGames
- Target: src/features/auth/AuthPage.test.tsx
- Scope: Integration tests verifying the correct rendering of the authentication page and mocking of the Google OAuth dependencies.
- Status: PASS

### Backend: FastAPI
- Target: tests/test_auth_utils.py
- Scope: Unit tests verifying password hashing, hash verification logic, and JWT access token creation.
- Status: PASS

- Target: tests/test_auth_endpoints.py
- Scope: Integration tests verifying the health check endpoint and the mock login endpoint responses using an asynchronous test client.
- Status: PASS

## 4. Configuration Notes

- Backend Database: The backend tests are configured to use a test database named "eduai_test_db". By default, it connects to a local instance at "mongodb://localhost:27017". To use a separate Atlas cluster for testing, provide the "TEST_MONGODB_URL" environment variable.
- React 19 Support: Testing Library for React was updated to version 16.2.0 to ensure full compatibility with React 19.

---
Generated on branch: testing-setup
Overall Status: All tests passing.
