# JOIN 360 — Django REST Backend

This repository contains the Django REST Framework backend for JOIN 360.

## Project context

The frontend of JOIN 360 was developed collaboratively as a team project. I independently developed the complete backend using Python, Django and Django REST Framework and integrated it with the frontend.

**Frontend repository:** [AhmetB-Dev/Join](https://github.com/AhmetB-Dev/Join)

## Stack

- Python
- Django
- Django REST Framework
- SQLite for local development
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
- Health and database-readiness endpoints
- Environment-based production configuration

## Start locally

Create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Recommended when backend/ lives inside the JOIN project root:
Copy-Item .env.example ..\.env
python manage.py migrate
python manage.py runserver
```

The API is then available at:

```text
http://127.0.0.1:8000/api/
```

## Environment variables

`.env` is intentionally ignored by Git. The backend first looks for `.env` in the JOIN project root and falls back to `backend/.env` for standalone use. Copy `.env.example` and change values for the current environment.

Important production values:

```text
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<strong random secret>
DJANGO_ALLOWED_HOSTS=example.com,api.example.com
DJANGO_CORS_ALLOWED_ORIGINS=https://example.com
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
```

When Django is behind a trusted reverse proxy that sets `X-Forwarded-Proto`, enable:

```text
DJANGO_TRUST_PROXY_SSL_HEADER=True
```

HSTS remains disabled by default and should only be enabled after HTTPS works reliably in production.

## Data behavior

- Every persisted contact and task must have an owner at database level.
- Task progress is derived by the backend from completed subtasks; client-supplied progress values are ignored.
- Existing task progress values are recalculated once by migration so stored data matches the new rule.
- Blank subtask text is rejected instead of being silently dropped.
- Registered users start with an empty board and an empty contact list.
- Every user can only access their own contacts and tasks.
- Guest login automatically creates an isolated demo workspace with fictional contacts, tasks and subtasks.
- Guest demo data is deleted together with the temporary guest account when the user logs out.
- No Firebase export or manual seed command is required.

The demo identities use `example.com` addresses and placeholder phone numbers. They are presentation data, not real people.

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

```powershell
python manage.py check
python manage.py test
```

Before production deployment also run:

```powershell
python manage.py check --deploy
```

## Production roadmap

The current repository intentionally keeps SQLite for local development. Before the public deployment, the production database, Docker runtime, reverse proxy/HTTPS setup, shared Redis use cases, and CI/CD pipeline will be configured explicitly for the target VPS instead of being guessed in advance.

## Security and data-isolation checks

The API keeps the existing simple e-mail/password login flow. Registration returns a token immediately; no e-mail verification/activation flow is required for this project.

The test suite explicitly verifies that:

- unauthenticated users cannot access contacts, tasks, `/me/` or logout,
- users cannot read, update or delete another user's contacts/tasks by guessing an ID,
- task/contact list filters remain scoped to the authenticated user,
- passwords are stored through Django password hashing and are never returned by the API,
- unknown-account and wrong-password login attempts use the same generic error response,
- logout deletes the active DRF token,
- task input rejects invalid columns, priorities, dates and blank subtasks,
- task progress cannot be manipulated by the client and is recalculated from subtasks,
- contact assignment never reuses another user's contact with the same name.

Auth throttling is intentionally not implemented with a process-local production cache. The public deployment will add rate limits together with the planned shared-cache/Redis setup so limits remain consistent across production workers.

## Phase 3 migration safety

The owner fields used to be nullable for legacy compatibility. Phase 3 makes them database-required. The migrations deliberately **do not delete or guess ownership for legacy rows**. If an older local database still contains owner-less contacts or tasks, `python manage.py migrate` stops with a clear error. Assign those legacy rows to the correct user first, then run the migration again.

This fail-closed migration behavior protects existing data from accidental reassignment or deletion.
