# National University of Rwanda Online Learning System (MVP)

This repository now contains a runnable MVP for an online learning system with:

- account registration and login (admin, lecturer, student),
- course creation (lecturer/admin),
- student enrollment,
- assignment creation,
- student submission flow,
- simple dashboard UI,
- health endpoint for monitoring.

## Tech stack

- Python 3.12
- FastAPI
- Jinja2 templates
- SQLite

## Project structure

```
app/
  main.py            # FastAPI app + routes
  database.py        # SQLite schema and connection helpers
  auth.py            # Password hashing + sessions
  templates/         # HTML UI templates
  static/            # CSS styles
tests/
  test_app.py        # smoke and flow tests
```

## Quick start

1) Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies:

```bash
pip install -r requirements.txt
```

3) Run the app:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4) Open:

- Home: http://localhost:8000/
- Health: http://localhost:8000/api/health

## Run tests

```bash
pytest -q
```

## Default behavior

- The database file is created automatically at `app/data/learning.db`.
- You can override DB location using `LEARNING_DB_PATH`.

## Suggested next features

- quiz engine,
- grades and lecturer feedback,
- file uploads for assignment attachments,
- announcements and forums,
- analytics dashboard,
- production authentication (SSO/JWT) and RBAC hardening.
