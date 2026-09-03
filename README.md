# EduAI Suite

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![React Version](https://img.shields.io/badge/React-19-blue)](https://reactjs.org/)
[![TypeScript Version](https://img.shields.io/badge/TypeScript-6-blue)](https://www.typescriptlang.org/)
[![FastAPI Version](https://img.shields.io/badge/FastAPI-0.104-green)](https://fastapi.tiangolo.com/)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-yellow)](https://www.python.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.x-green)](https://www.mongodb.com/)
[![Supabase](https://img.shields.io/badge/Supabase-integrated-blue)](https://supabase.com/)
[![Groq AI](https://img.shields.io/badge/Groq-AI-orange)](https://groq.com/)
[![Vite](https://img.shields.io/badge/Vite-5.0-purple)](https://vitejs.dev/)
[![Vitest](https://img.shields.io/badge/Vitest-1.0-pink)](https://vitest.dev/)
[![Pytest](https://img.shields.io/badge/Pytest-8.0-blue)](https://docs.pytest.org/)

## Overview

EduAI Suite is a comprehensive, open-source monorepo designed to revolutionize education through AI-assisted teaching, student learning, assessments, collaboration, and real-time classroom activities. Built with modern technologies, it provides two interconnected React applications powered by a shared FastAPI backend service.

> **Key Innovation**: EduAI Suite uniquely combines AI-powered features (via Groq) with collaborative tools (Trello-style planning, real-time WebSockets) and comprehensive assessment systems (OMR processing, automated grading) to create an all-in-one educational platform.

## 🏗️ Architecture

### Monorepo Structure
```
EduAI_Suite/
├── apps/
│   ├── teacherbuddy/          # React + TypeScript teacher/admin workspace
│   │   ├── src/
│   │   │   ├── features/      # Domain-specific features (20+ modules)
│   │   │   ├── layouts/       # Application shells (DashboardShell, StudentShell)
│   │   │   ├── router/        # Type-safe route configuration
│   │   │   ├── shared/        # Reusable UI components, hooks, utilities
│   │   │   └── store/         # Zustand state management
│   │   └── package.json       # Vite, React Router, TanStack Query, etc.
│   └── edugames/              # React + TypeScript student learning portal
│       └── src/               # Identical feature-oriented structure
├── backend/
│   ├── app/
│   │   ├── models/            # Pydantic + Beanie ODM models (15+ entities)
│   │   ├── routes/            # REST API routers (30+ endpoints)
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── services/          # Business logic (AI, storage, document processing)
│   │   ├── utils/             # Authentication, file, email utilities
│   │   └── main.py            # FastAPI application entrypoint
│   ├── tests/                 # Comprehensive test suite
│   ├── requirements.txt       # Production dependencies
│   ├── requirements-test.txt  # Test dependencies
│   ├── Dockerfile             # Containerized deployment
│   └── pytest.ini             # Test configuration
├── .github/
│   └── workflows/             # CI/CD pipelines
│       └── ci.yml             # GitHub Actions workflow
├── supabase/                  # Database migrations & storage config
├── TESTING_README.md          # Detailed testing documentation
└── package.json               # npm workspace configuration
```

### Technology Stack

#### Frontend Applications (TeacherBuddy & EduGames)
- **Framework**: React 19 with Concurrent Mode support
- **Language**: TypeScript 6 (strict mode enabled)
- **Build Tool**: Vite 5 (with React plugin)
- **State Management**: Zustand (lightweight, scalable alternative to Redux)
- **Data Fetching**: TanStack Query v5 (automatic caching, background updates)
- **Routing**: React Router DOM v7 (data routers, lazy loading)
- **UI Framework**: Tailwind CSS 4.2 (utility-first, JIT compilation)
- **Animations**: Framer Motion 12 (physics-based, accessible animations)
- **Icons**: Lucide React (consistent, lightweight icon set)
- **Drag & Drop**: @hello-pangea/dnd (accessible, touch-friendly)
- **OAuth**: @react-oauth/google (secure Google authentication)
- **Charts**: Recharts & D3 (data visualization for analytics)
- **Testing**: Vitest + React Testing Library (component & integration tests)
- **Linting**: ESLint + Prettier (code quality enforcement)

#### Backend Service
- **Framework**: FastAPI 0.104+ (async-first, automatic OpenAPI docs)
- **Language**: Python 3.10+ (with type hints)
- **Database**: MongoDB via Motor/Beanie ODM (async, schema-flexible)
- **AI Integration**: Groq API (low-latency LLM inference)
- **File Storage**: Supabase Storage (CDN-backed, secure file handling)
- **Email**: SMTP integration (notifications, password reset)
- **Real-time**: WebSocket support (live collaboration, updates)
- **Authentication**: JWT + Python-Jose (secure token handling)
- **Password Security**: Passlib + bcrypt (industry-standard hashing)
- **Document Processing**: 
  - PDF: PyMuPDF, PyPDF2 (text extraction, manipulation)
  - DOCX: Python-docx (document generation)
  - Images: Pillow, OpenCV (processing, OCR preprocessing)
  - OMR: Custom implementation (optical mark recognition)
- **NLP**: NLTK (text analysis, sentiment processing)
- **Data Analysis**: Pandas, NumPy, SciPy (educational analytics)
- **Testing**: Pytest + Pytest-Asyncio + HTTPX (comprehensive test suite)
- **Containerization**: Docker (consistent deployment across environments)
- **CI/CD**: GitHub Actions (automated testing, building, deployment)

## 🚀 Features

### TeacherBuddy (Teacher & Administrator Workspace)
- **Dashboard**: Real-time analytics, course overviews, student progress tracking
- **Classroom Management**: Course creation, student enrollment, scheduling
- **Lesson Planning**: Drag-and-drop curriculum builder, resource management
- **Assessment Tools**: 
  - Exam creator with multiple question types
  - Automated grading (objective questions)
  - OMR processing (scan & grade paper exams)
  - Rubric-based evaluation
  - Analytics & reporting dashboard
- **Collaboration**: 
  - Trello-style project & task boards
  - Real-time co-editing (WebSocket-powered)
  - Internal messaging system
  - Announcement system
- **Content Management**: 
  - Resource library (files, links, multimedia)
  - AI-powered content generation (Groq integration)
  - Presentation tools (live sessions, slide sharing)
  - Word cloud generator (student feedback visualization)
- **Administrative**: 
  - User management (roles, permissions)
  - Attendance tracking
  - Appointment scheduling (office hours, consultations)
  - Email communication tools
  - Audit trails & activity logs

### EduGames (Student Learning Portal)
- **Personal Dashboard**: Course overview, upcoming assignments, progress metrics
- **Learning Spaces**: 
  - Interactive classrooms (real-time participation)
  - Digital textbooks & resources
  - Assignment submission & feedback
  - Exam taking interface (with timer & accommodations)
  - Gradebook & performance analytics
- **Engagement Features**:
  - AI Chat Assistant (context-aware tutoring)
  - Educational games (quiz-based, word clouds, Slido-style polling)
  - Live presentation participation (Q&A, reactions, polls)
  - Wellness check-ins & mood tracking
  - Peer collaboration spaces
- **Gamification**: 
  - Achievement badges & progress tracking
  - Leaderboards (course & classroom level)
  - Points system for participation
  - Streak rewards for consistent engagement
- **Communication**:
  - In-app messaging (teacher & peer communication)
  - Notification system (assignments, grades, announcements)
  - Calendar integration (deadlines, events, schedules)
  - Video conferencing links (Zoom/Teams/Meet integration)

### Shared Capabilities
- **Authentication**: Secure Google OAuth + email/password fallback
- **Real-time Sync**: WebSocket connections for live updates
- **Responsive Design**: Mobile-first approach (works on tablets & phones)
- **Accessibility**: WCAG 2.1 compliant (ARIA labels, keyboard navigation)
- **Internationalization**: Ready for i18n (English baseline)
- **Data Export**: CSV/Excel export for reports & analytics
- **Backup & Recovery**: Automated backup strategies
- **Performance Optimization**: Code splitting, lazy loading, caching
- **Security**: 
  - Input validation & sanitization
  - Rate limiting & brute force protection
  - Secure headers & CORS configuration
  - Environment-based configuration
  - Dependency vulnerability scanning

## 🔧 Backend API Endpoints

The backend provides a comprehensive RESTful API with WebSocket support:

### Core Resources
- **Authentication**: `/api/auth/*` (login, logout, token refresh, password reset)
- **Users**: `/api/users/*` (CRUD operations, role management)
- **Courses**: `/api/courses/*` (creation, enrollment, curriculum)
- **Lessons**: `/api/lessons/*` (planning, resources, assignments)
- **Exams**: `/api/exams/*` (creation, taking, grading, analytics)
- **Assignments**: `/api/assignments/*` (creation, submission, feedback)
- **Submissions**: `/api/submissions/*` (tracking, feedback, resubmission)
- **Appointments**: `/api/appointments/*` (scheduling, reminders, video links)

### Specialized Services
- **AI Chat**: `/api/ai/chat` (context-aware conversations with Groq)
- **OMR Processing**: `/api/omr/*` (upload, process, grade paper exams)
- **Word Cloud**: `/api/wordcloud/*` (generate from text responses)
- **Analytics**: `/api/analytics/*` (performance trends, engagement metrics)
- **Reports**: `/api/reports/*` (customizable PDF/Excel exports)
- **Calendar**: `/api/calendar/*` (events, deadlines, scheduling)
- **Mail**: `/api/mail/*` (SMTP integration, templated emails)
- **Trello Boards**: `/api/trello/*` (boards, lists, cards, collaboration)
- **Games**: `/api/games/*` (educational games, scoring, leaderboards)
- **WebSocket**: `/api/ws/*` (real-time updates, live collaboration)
- **Admin**: `/api/admin/*` (system monitoring, user management, settings)

### API Documentation
- **Swagger UI**: Available at `/docs` when running locally
- **ReDoc**: Available at `/redoc` when running locally
- **OpenAPI Spec**: Auto-generated from FastAPI annotations
- **Versioning**: Path-based versioning planned for future releases

## ⚙️ Setup & Installation

### Prerequisites
- **Node.js**: Version 22.x (LTS) - [Download](https://nodejs.org/)
- **Python**: Version 3.10 or newer - [Download](https://www.python.org/downloads/)
- **MongoDB**: Version 4.x or Atlas cluster - [Installation Guide](https://docs.mongodb.com/manual/installation/)
- **Git**: Version 2.x or newer - [Download](https://git-scm.com/downloads)

### Environment Variables
Create a `.env` file in the `backend/` directory based on `.env.example`:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_STORAGE_BUCKET=your_storage_bucket_name
MONGODB_URL=mongodb://localhost:27017/eduai_suite

# Optional (for full functionality)
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
SMTP_HOST=your_smtp_server
SMTP_PORT=587
SMTP_USER=your_smtp_username
SMTP_PASS=your_smtp_password
TEACHER_DOMAIN=your_institution_domain
ADMIN_EMAIL=admin@your_institution_domain
```

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/EduAI_Suite.git
   cd EduAI_Suite
   ```

2. **Install Frontend Dependencies**
   ```bash
   npm install
   ```

3. **Setup Backend Environment**
   ```bash
   cd backend
   python -m venv venv
   
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   
   # macOS/Linux:
   # source venv/bin/activate
   
   pip install -r requirements.txt
   cd ..
   ```

4. **Configure Environment**
   ```bash
   # Windows PowerShell:
   Copy-Item backend/.env.example backend/.env
   
   # macOS/Linux:
   # cp backend/.env.example backend/.env
   
   # Edit backend/.env with your actual values
   notepad backend/.env  # Windows
   # nano backend/.env   # macOS/Linux
   ```

5. **Initialize Database**
   ```bash
   # Ensure MongoDB is running (mongod --dbpath ./data)
   # The backend will automatically create collections on first startup
   ```

### Development Setup

#### Start All Services
```bash
# From repository root:
npm run dev
```
- TeacherBuddy: http://localhost:5173
- EduGames: http://localhost:5174
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

#### Individual Services
```bash
# TeacherBuddy only
npm run dev:admin

# EduGames only  
npm run dev:interactive

# Backend only
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🧪 Testing

### Test Frameworks
- **Frontend**: Vitest + React Testing Library + User Event
- **Backend**: Pytest + Pytest-Asyncio + HTTPX
- **Database**: Real MongoDB test database (isolated from production)

### Running Tests
```bash
# Install backend test dependencies
python -m pip install -r backend/requirements-test.txt

# Run all tests (frontend + backend)
npm run test

# Run specific test suites
npm run test:teacherbuddy   # TeacherBuddy Vitest tests
npm run test:edugames       # EduGames Vitest tests  
npm run test:backend        # Backend Pytest tests
```

### Test Coverage
- **Authentication Systems**: Login/logout, token validation, password reset
- **Core Features**: Course management, lesson planning, exam creation
- **AI Integration**: Context-aware responses, prompt safety, token limits
- **File Processing**: Upload handling, virus scanning, format validation
- **Real-time Features**: WebSocket connections, broadcast mechanisms
- **Edge Cases**: Error handling, timeout scenarios, malformed inputs

See [TESTING_README.md](TESTING_README.md) for detailed testing strategy and current outcomes.

## 🐳 Docker Deployment

### Prerequisites
- Docker Engine 20.10+
- Docker Compose v2+
- Configured Supabase variables in repository `.env` file

### Deployment
```bash
# Copy Supabase variables to root .env (if not already done)
# docker compose up --build
```

The backend will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs

### Production Considerations
1. Create the `SUPABASE_STORAGE_BUCKET` bucket in Supabase Dashboard
2. Configure proper CORS settings for your domain
3. Set up SSL termination at reverse proxy level (NGINX/TRAEFIK)
4. Configure environment-specific variables (DEBUG=false, etc.)
5. Set up automated backups for MongoDB database
6. Configure monitoring & logging (ELK stack, Prometheus/Grafana)
7. Implement rate limiting & DDoS protection at infrastructure level

## 📦 Available Scripts

### Root Level (package.json)
```bash
npm run dev                 # Start TeacherBuddy & EduGames together
npm run dev:admin           # Start TeacherBuddy only
npm run dev:interactive     # Start EduGames only
npm run test                # Run frontend & backend tests
npm run test:teacherbuddy   # TeacherBuddy test suite
npm run test:edugames       # EduGames test suite
npm run test:backend        # Backend test suite
npm run build               # Build both applications for production
```

### TeacherBuddy (apps/teacherbuddy/package.json)
```bash
npm run dev                 # Start development server
npm run build               # Build for production
npm run lint                # Run ESLint
npm run preview             # Preview production build
npm run test                # Run Vitest tests
```

### EduGames (apps/edugames/package.json)
```bash
npm run dev                 # Start development server
npm run build               # Build for production
npm run lint                # Run ESLint
npm run preview             # Preview production build
npm run test                # Run Vitest tests
```

### Backend (backend/requirements.txt)
```bash
python -m pip install -r requirements.txt  # Install dependencies
uvicorn app.main:app --reload              # Development server
python -m pytest                           # Run test suite
```

## 🔒 Security Considerations

### Authentication & Authorization
- JWT tokens with 15-minute expiration & refresh mechanism
- Password hashing using bcrypt (salt rounds: 12)
- Role-based access control (RBAC) with fine-grained permissions
- Session invalidation on password change/logout from all devices
- OAuth 2.0 compliance for Google authentication
- Account locking after failed login attempts (configurable threshold)

### Data Protection
- Environment variable separation (no secrets in code)
- HTTPS enforcement in production (via reverse proxy)
- CORS restrictions to trusted domains
- Input validation & sanitization on all endpoints
- File upload validation (type, size, virus scanning)
- SQL/NoSQL injection prevention (ODM/ORM usage)
- Regular dependency security audits

### Privacy & Compliance
- GDPR-ready data handling procedures
- Data export & deletion capabilities
- Audit logging for sensitive operations
- Configurable data retention policies
- Anonymization options for analytics
- Consent tracking for data processing

## 🤝 Contributing

We welcome contributions from the education technology community! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests: `npm run test`
5. Commit changes: `git commit -m 'feat: amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Coding Standards
- Follow existing code style (ESLint/Prettier configuration)
- Write meaningful commit messages (Conventional Commits)
- Add tests for new features & bug fixes
- Update documentation when changing APIs
- Perform self-review before submitting PRs
- Ensure cross-browser compatibility for UI changes

### Issue Reporting
- Use descriptive titles & clear descriptions
- Include steps to reproduce for bugs
- Suggest expected vs actual behavior
- Label appropriately (bug, enhancement, question, etc.)
- Check existing issues before reporting new ones

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Groq** for providing lightning-fast AI inference
- **Supabase** for excellent backend-as-a-service platform
- **MongoDB** for flexible, scalable document database
- **Vite Team** for the blazing fast frontend build tool
- **React Team** for the incredible UI library
- **FastAPI Team** for the modern, async Python framework
- **Open Source Community** for countless libraries that make this possible
- **Educators & Students** who provide invaluable feedback for improvement

## 📞 Support & Community

- **Documentation**: See this README and linked documents
- **Issue Tracker**: GitHub Issues for bug reports & feature requests
- **Discussions**: GitHub Discussions for questions & ideas
- **Security Issues**: Please email security@yourdomain.com for responsible disclosure
- **Enterprise Support**: Available for institutional deployments (contact for details)

---

*Built with ❤️ for educators and learners everywhere. Transforming education through technology, one classroom at a time.*

**Last Updated**: September 2026  
**Version**: 1.0.0  
**Maintained by**: Omkaar Chakraborty