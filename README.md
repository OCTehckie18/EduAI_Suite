# EduAI Suite

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![React](https://img.shields.io/badge/React-19-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-6-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-green)
![Python](https://img.shields.io/badge/Python-3.10%2B-yellow)

EduAI Suite is a monorepo for AI-assisted teaching, student learning, assessments, collaboration, and real-time classroom activities. It contains two React applications backed by a shared FastAPI service.

## Applications

- **TeacherBuddy** (`apps/teacherbuddy`) — teacher and administrator workspace for dashboards, courses, lessons, exams, analytics, reports, OMR processing, presentations, games, appointments, mail, and Trello-style planning.
- **EduGames** (`apps/edugames`) — student workspace for dashboards, classrooms, lessons, exams, live presentations, wellbeing, appointments, AI chat, games, and Trello-style planning.
- **Backend API** (`backend`) — FastAPI application providing authentication, course and classroom workflows, lessons, exams, assignments, games, analytics, reports, OMR, storage, email, and WebSocket features.

The main product apps communicate with the backend through the `/api` proxy. The Vite development servers also proxy WebSocket traffic to the backend.

## Current structure

```text
EduAI_Suite/
├── apps/
│   ├── teacherbuddy/          # React + TypeScript teacher/admin app
│   │   └── src/
│   │       ├── features/      # Product features
│   │       ├── layouts/        # Application shells
│   │       ├── router/         # Route configuration
│   │       ├── shared/         # Reusable UI, hooks, and utilities
│   │       └── store/          # Client state
│   └── edugames/              # React + TypeScript student app
│       └── src/               # Same feature-oriented layout as TeacherBuddy
├── backend/
│   ├── app/
│   │   ├── models/            # Persistence models
│   │   ├── routes/             # REST and WebSocket routes
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # AI, storage, document, and domain services
│   │   └── utils/              # Authentication and file utilities
│   ├── tests/                 # Backend tests
│   ├── requirements.txt
│   ├── requirements-test.txt
│   └── pytest.ini
├── .github/workflows/ci.yml   # Frontend and backend CI
├── supabase/                   # Supabase migrations and configuration
├── TESTING_README.md          # Detailed testing notes
└── package.json               # npm workspace and root scripts
```

## Technology

- React, TypeScript, Vite, React Router, Tailwind CSS, Zustand, TanStack Query, Framer Motion, and Vitest for the frontend.
- Python, FastAPI, Uvicorn, Pydantic, Motor/Beanie, and Pytest for the backend.
 - MongoDB is used by the backend persistence layer. Supabase Storage is used for uploaded files and generated assets.
- Groq is used for AI-powered features. Google OAuth and SMTP integrations are configured through environment variables.

## Prerequisites

- Node.js 22 (the CI workflow uses Node 22)
- Python 3.10 or newer
- MongoDB for backend development and tests
- A Groq API key for AI features
 - Optional: Supabase Storage, Google OAuth credentials, and SMTP credentials

## Setup

Clone the repository and install the frontend dependencies:

```bash
git clone <repository-url>
cd EduAI_Suite
npm install
```

Create and activate a Python virtual environment, then install the backend dependencies:

```bash
cd backend
python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
# source venv/bin/activate
python -m pip install -r requirements.txt
cd ..
```

Copy the environment template and fill in the values needed for your setup:

```bash
Copy-Item backend/.env.example backend/.env       # Windows PowerShell
# cp backend/.env.example backend/.env             # macOS/Linux
```

At minimum, configure `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_STORAGE_BUCKET`. The template also documents MongoDB, Supabase Auth/Storage, Google OAuth, SMTP, teacher-domain, and admin-email settings used by the backend.

## Run locally

Start both frontend applications from the repository root:

```bash
npm run dev
```

- TeacherBuddy: <http://localhost:5173>
- EduGames: <http://localhost:5174>

Start the backend in a separate terminal with the virtual environment activated:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API: <http://localhost:8000>
 - Swagger UI: <http://localhost:8000/docs>

## Docker

Copy the Supabase variables from backend/.env into the repository .env, then run docker compose up --build.

The backend is available at http://localhost:8000. To use the published image,
set DOCKERHUB_USERNAME and BACKEND_IMAGE_TAG in .env.

Create the `SUPABASE_STORAGE_BUCKET` bucket in the Supabase Dashboard before uploading files. The backend uses the service-role key to upload, download, delete, and sign files server-side.

## Commands

Run these from the repository root:

```bash
npm run dev                 # Start TeacherBuddy and EduGames together
npm run dev:admin           # Start TeacherBuddy only
npm run dev:interactive     # Start EduGames only
npm run test                # Run frontend and backend tests
npm run test:teacherbuddy   # TeacherBuddy Vitest suite
npm run test:edugames       # EduGames Vitest suite
npm run test:backend        # Backend Pytest suite
```

Each frontend also provides `build`, `lint`, and `preview` scripts through its workspace package. For backend test setup, install `backend/requirements-test.txt` when required:

```bash
python -m pip install -r backend/requirements-test.txt
```

## Continuous integration

GitHub Actions runs the TeacherBuddy and EduGames test/build checks plus the backend Pytest suite. The backend CI job starts MongoDB 7 as a service. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for the exact workflow.

## License

This project is licensed under the MIT License.
