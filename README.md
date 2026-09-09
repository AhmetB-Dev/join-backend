# JOIN 360 — Django REST API

Production-oriented Django REST Framework backend for **JOIN 360**, a task and contact management application.

The JOIN frontend was originally developed as a team project. I independently designed and implemented this backend, including the API contract integration, data isolation, PostgreSQL/Redis runtime, automated tests, Docker setup and CI/CD deployment.

**Frontend repository:** [AhmetB-Dev/Join](https://github.com/AhmetB-Dev/Join)  
**Production API:** `https://join-api.ahmet-balci.de/api/`  
**Health endpoint:** `https://join-api.ahmet-balci.de/api/health/`

## What this backend demonstrates

- Django REST Framework API design and token-based authentication
- User-scoped data access for contacts and tasks
- PostgreSQL as the production database
- Redis-backed shared cache and API throttle state
- Docker Compose health/readiness checks
- Gunicorn production runtime behind Nginx and HTTPS
- Environment-driven security configuration with production fail-closed checks
- Automated CI for linting, dependency auditing and Django tests
- Immutable container-image publishing to GHCR
- Automated VPS deployment with health validation and application-image rollback

## Technology stack

| Area | Technology |
| --- | --- |
| Backend | Python 3.14, Django 6, Django REST Framework |
| Authentication | DRF token authentication |
| Database | SQLite for simple local development, PostgreSQL for Docker/production |
| Cache / throttling | Redis |
| Application server | Gunicorn |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions, GHCR, SSH deployment |
| Reverse proxy | Nginx + Let's Encrypt HTTPS |
| Quality | Ruff, pip-audit, Django tests |

## Core features

- Registration, login, guest login, logout and authenticated user lookup
- Contacts CRUD with strict per-user ownership
- Tasks CRUD with strict per-user ownership
- Contact assignment to tasks
- Subtasks with backend-derived completion progress
- Isolated guest demo workspaces with automatically generated demo data
- Health endpoint for process liveness
- Readiness endpoint that verifies PostgreSQL and Redis connectivity
- User-scoped task-list caching with explicit invalidation
- Scoped rate limiting for public authentication endpoints

## Architecture

```text
Browser / JOIN frontend
        |
      HTTPS
        |
      Nginx
        |
  127.0.0.1:8001
        |
  Django + Gunicorn
      /       \
     /         \
PostgreSQL    Redis
source of     cache + shared
truth         throttle state
```

The web container is published only on the VPS loopback interface. Nginx terminates HTTPS and forwards requests to the application. Redis is intentionally non-persistent because cached data and throttle counters are disposable; PostgreSQL remains the authoritative data store.

## API overview

```text
GET    /api/
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

## Local development

### 1. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

For local PostgreSQL development, install the production additions as well:

```powershell
pip install -r requirements-production.txt
```

### 3. Create local environment configuration

```powershell
Copy-Item .env.example .env
```

The defaults support simple local development with SQLite and Django's in-process LocMem cache. Adjust `.env` if the frontend runs on a different local origin.

### 4. Prepare and start Django

```powershell
python manage.py migrate
python manage.py runserver
```

The API is then available at:

```text
http://127.0.0.1:8000/api/
```

## Docker development stack

The Docker stack uses Django/Gunicorn, PostgreSQL and Redis.

```powershell
docker compose --env-file .env build
docker compose --env-file .env run --rm web python manage.py migrate
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

Useful checks:

```powershell
docker compose --env-file .env run --rm web python manage.py check
docker compose --env-file .env run --rm web python manage.py test
```

Stop the stack while preserving PostgreSQL data:

```powershell
docker compose --env-file .env down
```

> `docker compose down -v` removes the PostgreSQL volume. Use it only when the database data is intentionally disposable.

## Environment configuration

Real `.env` files are ignored by Git. Use:

- `.env.example` for local development
- `.env.production.example` as the documented production template

Production intentionally rejects unsafe configuration. With `DJANGO_DEBUG=False`, JOIN requires a non-placeholder Django secret, PostgreSQL, a real database password, allowed hosts and shared Redis.

The production reverse-proxy settings are important because Nginx terminates HTTPS before forwarding traffic to Django:

```env
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_TRUST_PROXY_SSL_HEADER=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
```

`DJANGO_ALLOWED_HOSTS` also contains `127.0.0.1` and `localhost` because the Docker healthcheck calls the readiness endpoint from inside the web container.

## Security and data isolation

- Every persisted task and contact has an owner at database level.
- Querysets are restricted to the authenticated user.
- Task progress is derived from subtasks; client-supplied progress is not trusted.
- Blank subtask text is rejected.
- Public auth endpoints have scoped throttling backed by Redis in production.
- Production refuses SQLite and known development/placeholder secrets.
- Secure cookies, HTTPS redirect and proxy-aware HTTPS detection are configurable through environment variables.
- The API container is bound to `127.0.0.1` on the VPS and exposed publicly through Nginx only.

No system is presented as "unhackable"; the project instead uses layered controls, least exposure and explicit production validation.

## Caching behavior

The unfiltered `GET /api/tasks/` response is cached per authenticated user because the JOIN summary view polls that endpoint frequently. Filtered task requests bypass the cache. Task and contact mutations invalidate affected task-cache entries, and a short TTL provides an additional fallback.

Redis is never used as the source of truth.

## Testing and quality checks

Run the Django checks and test suite locally:

```powershell
python manage.py check
python manage.py test
```

Production-oriented Django checks:

```powershell
python manage.py check --deploy
```

CI additionally runs Ruff and dependency vulnerability auditing before a production image can be published.

## CI/CD

JOIN uses the shared reusable workflow standard from `AhmetB-Dev/django-devops-template@v1`.

```text
Pull request
  -> lint + dependency audit
  -> PostgreSQL/Redis Django test stack

Push to main
  -> CI
  -> immutable GHCR image (commit SHA)
  -> production environment gate
  -> SSH deployment to VPS
  -> migrations
  -> Docker health/readiness validation
  -> rollback to previous application image if rollout fails
```

Production deployment details are documented in [`DEPLOYMENT.md`](DEPLOYMENT.md).

## Repository structure

```text
contacts/             Contacts domain
core/                 API root, health and readiness endpoints
tasks/                Tasks, subtasks, caching and API logic
users/                Custom user model and authentication flows
config/               Django project configuration
scripts/deploy.sh      Production deployment / rollback script
compose.yml            Local Docker stack
compose.ci.yaml        CI integration-test stack
compose.prod.yaml      Production Compose stack
.github/workflows/     Project CI/CD entrypoint
```

## Data migration note

Django migrations create database schemas; they do not automatically copy rows between SQLite and PostgreSQL. If existing SQLite development data must be moved to PostgreSQL, export/import it explicitly rather than treating schema migration as data migration.
