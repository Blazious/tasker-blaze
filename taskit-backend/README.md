# Taskit Backend

Django backend scaffold for the Taskit project.

## Stack

- Django 4.2
- Django REST Framework
- Django Channels with Redis channel layer
- Simple JWT
- django-allauth
- Cloudinary storage
- Celery and Redis

## Local Setup

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create your local environment file:

```powershell
Copy-Item .env.example .env
```

4. Run migrations:

```powershell
python manage.py migrate
```

5. Start the development server:

```powershell
python manage.py runserver
```

The API is wired under:

```text
http://127.0.0.1:8000/api/v1/
```

## Settings

The project uses split settings:

- `config/settings/base.py`
- `config/settings/dev.py`
- `config/settings/prod.py`

Local development defaults to `config.settings.dev`, which uses SQLite and allows all CORS origins.
