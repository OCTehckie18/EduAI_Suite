# Local Docker testing

This Compose setup is for local development before pushing changes. It keeps
application data inside the local MongoDB container and uses Supabase only for
authentication and profile synchronization.

## Data boundaries

- Frontends: `http://localhost:5173` and `http://localhost:5174`
- Backend: `http://localhost:8000`
- MongoDB from the host: `mongodb://localhost:27017`
- MongoDB from the backend container: `mongodb://mongodb:27017`
- Local database: `eduai_suite_local`
- Local Mongo volume: `mongodb_local_data`
- Supabase: authentication/profile identity only

The backend Compose environment intentionally fixes `MONGODB_URL` and
`MONGODB_DB`, so a remote MongoDB URL in a developer `.env` file cannot be
used by the Docker backend.

## Start local services

From the repository root, with Docker Desktop running:

```powershell
docker compose up -d --build
```

Do not run Uvicorn or Vite separately on ports 8000, 5173, or 5174 while the
Compose services are running.

Check the services:

```powershell
docker compose ps
docker compose logs -f backend
```

Open TeacherBuddy at `http://localhost:5173`. On the first login, Supabase
authenticates the account and the local backend creates the corresponding
profile in the local `eduai_suite_local` database.

## Reset local application data

This removes only the dedicated local MongoDB volume and cannot affect the
remote MongoDB database:

```powershell
docker compose down
docker volume rm eduai_suite_mongodb_local_data
docker compose up -d --build
```

After a reset, log in again and recreate local courses, students, and other
test data.
