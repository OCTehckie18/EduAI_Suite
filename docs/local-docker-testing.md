# Local testing

Local testing uses Uvicorn and Vite directly. Docker Compose is reserved for
deployment or self-contained Docker environments.

## Data boundaries

- Frontends: `http://localhost:5173` and `http://localhost:5174`
- Backend: `http://localhost:8000`
- Local MongoDB: `mongodb://localhost:27017`
- Supabase: authentication/profile identity only

Create `backend/.env.local` (ignored by Git) with:

```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=eduai_suite_local
```

Then run the backend and frontends directly:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd apps/teacherbuddy
npm run dev
```

The frontend `.env` files already point to `http://localhost:8000`.

## Compose deployment

Compose defaults to the Render API URL and bundled MongoDB. Set deployment
variables such as `MONGODB_URL`, `MONGODB_DB`, and `VITE_API_URL` in the
deployment environment when using external services.

```powershell
docker compose up -d --build
```
