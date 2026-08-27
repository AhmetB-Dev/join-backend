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
- Subtasks and progress
- Isolated guest demo workspaces
- REST API integration with the JOIN frontend

## Start locally

Create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The API is then available at:

```text
http://127.0.0.1:8000/api/
```

## Data behavior

- Registered users start with an empty board and an empty contact list.
- Every user can only access their own contacts and tasks.
- Guest login automatically creates an isolated demo workspace with fictional contacts, tasks and subtasks.
- Guest demo data is deleted together with the temporary guest account when the user logs out.
- No Firebase export or manual seed command is required.

The demo identities use `example.com` addresses and placeholder phone numbers. They are presentation data, not real people.

## API endpoints

```text
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

## Production notes

Before deployment, move `SECRET_KEY` to an environment variable, set `DEBUG = False`, configure `ALLOWED_HOSTS`, use a production database such as PostgreSQL, and restrict CORS to the deployed frontend origin.
