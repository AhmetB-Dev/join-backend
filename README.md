# JOIN 360 — Django REST Backend

This repository contains the Django REST Framework backend for JOIN 360.

## Project context

The frontend of JOIN 360 was developed collaboratively as a team project. I independently developed the complete backend using Python, Django and Django REST Framework and integrated it with the frontend.

**Frontend repository:** [AhmetB-Dev/Join](https://github.com/AhmetB-Dev/Join)

## Stack

- Python 3.14
- Django 6
- Django REST Framework
- SQLite for zero-dependency local development
- PostgreSQL for Docker/production
- Redis for shared cache and auth-throttle state
- Gunicorn as the container production application server
- Separate common vs. production-only dependency files
- Docker / Docker Compose
- Django REST Framework token authentication

## Main backend features

- Registration, login, guest login and logout
- User-specific contacts and tasks
- Contacts CRUD
- Tasks CRUD
- Task assignment to contacts
- Subtasks with server-calculated progress
- Isolated guest demo workspaces
- REST API integration with the JOIN frontend
- Health and dependency-readiness endpoints
- Environment-based production configuration
- User-scoped task-list caching with explicit invalidation
- Auth endpoint rate limiting with shared cache state
- PostgreSQL-backed Docker runtime with persistent database volume

## Start locally without Docker

Create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Gunicorn/PostgreSQL driver are installed only in Docker/production.
# For a local PostgreSQL setup, use: pip install -r requirements-production.txt
# Recommended when the backend lives inside the JOIN project root:
Copy-Item .env.example ..\.env
python manage.py migrate
python manage.py runserver
```

With `DB_ENGINE=sqlite` and no `REDIS_URL`, local development uses SQLite and Django's in-process LocMem cache.

The API is available at:

```text
http://127.0.0.1:8000/api/
```

The current JOIN frontend already points to `http://127.0.0.1:8000/api`, so running the backend container on port 8000 does not change the frontend API contract.

## Docker Compose: Django + PostgreSQL + Redis

Phase 5 adds a production-like local runtime with three containers:

```text
JOIN frontend (host / Live Server)
        |
        v
localhost:8000
        |
      web
   Django + Gunicorn
     /          \
    v            v
PostgreSQL      Redis
persistent      temporary shared state
```

PostgreSQL data is stored in the named Docker volume `postgres_data`. Redis is deliberately not persisted because JOIN uses it only for cache and throttle state; the database remains the source of truth.

**Important:** `python manage.py migrate` creates the schema in PostgreSQL but does not copy rows from an existing SQLite `db.sqlite3`. The SQLite file stays untouched. A new Docker PostgreSQL volume therefore starts with an empty application database. If existing local users/tasks/contacts must be preserved, export/import them deliberately instead of assuming schema migrations transfer data between database engines.

### First Docker start

Create an environment file. If your `.env` is in the parent JOIN folder, use it explicitly with `--env-file ../.env` in the commands below. For a standalone backend repository you can instead copy `.env.example` to `.env` next to `compose.yml`.

For local Docker development, set at least:

```text
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=django-insecure-docker-development-only
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DB_NAME=join
DB_USER=join
DB_PASSWORD=join-local-dev-password
```

Build the image:

```powershell
docker compose --env-file ../.env build
```

Apply migrations to PostgreSQL explicitly before starting the web service:

```powershell
docker compose --env-file ../.env run --rm web python manage.py migrate
```

Start the stack:

```powershell
docker compose --env-file ../.env up -d
```

Check container status:

```powershell
docker compose --env-file ../.env ps
```

Check the API:

```text
http://127.0.0.1:8000/api/health/
http://127.0.0.1:8000/api/readiness/
```

The readiness endpoint checks both the database and the configured cache. In Docker this means PostgreSQL and Redis must both be reachable before the web container is considered healthy.

Stop the containers without deleting database data:

```powershell
docker compose --env-file ../.env down
```

`docker compose down -v` deletes the PostgreSQL volume and therefore the Docker database. Do not use `-v` when you want to keep your data.

### Docker checks/tests

```powershell
docker compose --env-file ../.env run --rm web python manage.py check
docker compose --env-file ../.env run --rm web python manage.py test
```

Because the web service receives `DB_ENGINE=postgresql` and `REDIS_URL=redis://redis:6379/0` from Compose, these commands verify the application against the real supporting services rather than the SQLite/LocMem development fallbacks.

## Environment variables

`.env` is intentionally ignored by Git. The backend first looks for `.env` in the JOIN project root and falls back to the backend directory for standalone use.

Important values:

```text
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=<secret>
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=sqlite
DB_NAME=join
DB_USER=join
DB_PASSWORD=<database password>
DB_HOST=127.0.0.1
DB_PORT=5432
DB_CONN_MAX_AGE=60

REDIS_URL=
JOIN_TASK_CACHE_TIMEOUT=30
JOIN_LOGIN_RATE=10/min
JOIN_REGISTER_RATE=5/min
JOIN_GUEST_RATE=5/min
```

Docker Compose deliberately overrides `DB_ENGINE` to `postgresql`, `DB_HOST` to `db`, and `REDIS_URL` to `redis://redis:6379/0` inside the web container.

For production, JOIN fails closed when unsafe configuration is detected. Production requires:

```text
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<strong random production secret>
DJANGO_ALLOWED_HOSTS=<production hostnames>
DB_ENGINE=postgresql
DB_PASSWORD=<strong production database password>
REDIS_URL=<shared Redis URL>
```

SQLite is intentionally rejected when `DJANGO_DEBUG=False`, and known placeholder/development secrets are rejected in production.

## Cache and abuse protection

The unfiltered `GET /api/tasks/` response is cached per authenticated user because JOIN's summary page polls that endpoint frequently. Cache keys include the user ID, filtered task requests bypass this cache, and the cache is invalidated whenever tasks or contacts are created, updated or deleted. Redis is never the source of truth; the database remains authoritative and the cache also has a short TTL as a fallback.

Public auth entrypoints use DRF scoped throttling. Login, registration and guest login have separate limits. The same Django cache backend stores throttle state, so Docker/production workers share the same counters through Redis.

## Data behavior

- Every persisted contact and task must have an owner at database level.
- Task progress is derived by the backend from completed subtasks; client-supplied progress values are ignored.
- Blank subtask text is rejected instead of being silently dropped.
- Registered users start with an empty board and an empty contact list.
- Every user can only access their own contacts and tasks.
- Guest login automatically creates an isolated demo workspace with fictional contacts, tasks and subtasks.
- Guest demo data is deleted together with the temporary guest account when the user logs out.

## API endpoints

```text
GET    /api/health/
GET    /api/readiness/

POST   /api/auth/register/
POST   /api/auth/login/
POST   /api/auth/guest/
POST   /api/auth/logout/
GET    /api/auth/me/

GET    /api/contacts/
POST   /api/contacts/
GET    /api/contacts/<id>/
PUT    /api/contacts/<id>/
PATCH  /api/contacts/<id>/
DELETE /api/contacts/<id>/

GET    /api/tasks/
POST   /api/tasks/
GET    /api/tasks/<id>/
PUT    /api/tasks/<id>/
PATCH  /api/tasks/<id>/
DELETE /api/tasks/<id>/
```

## Checks and tests

Without Docker:

```powershell
python manage.py check
python manage.py test
```

Before public production deployment also run:

```powershell
python manage.py check --deploy
```

## Frontend compatibility

Phase 5 does not change registration, login, task, contact, or authentication response contracts. The current JOIN frontend can therefore continue using its existing `JoinAPI` integration unchanged.

The frontend still calculates and sends a `progress` field in task payloads. The backend intentionally ignores that client value and derives progress from subtasks, so the field is redundant but not breaking. It can be removed during a later frontend cleanup.

## Security and data isolation

The API keeps the existing simple e-mail/password login flow. Registration returns a token immediately; no e-mail verification/activation flow is required for this project.

The test suite verifies authentication, owner isolation, validation, token invalidation, cache isolation/invalidation, server-calculated progress and auth throttling. The readiness tests additionally cover database and cache failure behavior.

## Dependency split

`requirements.txt` contains dependencies needed for normal Windows/local development. `requirements-production.txt` extends it with Gunicorn and the PostgreSQL driver. This keeps the local Windows environment free of a Unix-only application server while the Docker image remains fully reproducible.

## Phase 5 infrastructure decisions

Phase 5 intentionally introduces only infrastructure with a concrete role:

- **PostgreSQL:** persistent production-grade relational database.
- **Redis:** shared task cache and shared DRF throttle counters.
- **Gunicorn:** production WSGI process instead of Django `runserver` inside the container.
- **Docker Compose:** reproducible local topology and a direct stepping stone to the Linux VPS deployment.

PostgreSQL and Redis are not exposed as host ports. Only the Django/Gunicorn web service publishes port `8000`. Database inspection can be performed through `docker compose exec db psql` instead of exposing the database publicly.

No Celery, Kubernetes, message broker workflow, microservices or other unrelated infrastructure is added because JOIN currently has no workload that requires them.

## Next production steps

Phase 5 deliberately stops before the public edge layer. The next steps are:

1. reverse proxy (Nginx),
2. HTTPS/TLS,
3. production static-file strategy,
4. VPS deployment,
5. CI/CD and automated migrations/deployment checks,
6. PostgreSQL backup/restore procedure.

## Phase 6: Continuous Integration

The repository includes `.github/workflows/backend-ci.yml`. GitHub Actions runs the backend checks automatically on every push and pull request.

The workflow deliberately reuses the same Docker Compose topology that is used locally instead of maintaining a separate CI-only database/cache setup. It performs:

1. `docker compose config --quiet`
2. Docker image build
3. PostgreSQL and Redis startup
4. Django migrations
5. missing-migration check
6. `python manage.py check`
7. the complete Django test suite
8. a real Gunicorn container startup
9. `/api/health/` and `/api/readiness/` smoke checks
10. automatic cleanup, with container logs printed if the job fails

CI uses non-production credentials defined only inside the workflow. No local `.env` file and no production secret is committed to the repository.

This is intentionally CI only. Automatic deployment is kept separate until the Linux VPS, reverse proxy and HTTPS configuration exist, so a successful push cannot accidentally deploy to an unfinished production environment.

### Local equivalent

The core CI sequence can still be reproduced locally:

```powershell
docker compose build
docker compose up -d db redis
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py test
docker compose up -d
curl.exe http://127.0.0.1:8000/api/health/
curl.exe http://127.0.0.1:8000/api/readiness/
```

## Next production steps after CI

1. provision the Linux VPS,
2. deploy the Docker stack with production environment values,
3. put Nginx in front of Gunicorn,
4. enable HTTPS/TLS for the real domain,
5. run `python manage.py check --deploy`,
6. add CD only after the first manual production deployment is proven,
7. document and test PostgreSQL backup/restore.
