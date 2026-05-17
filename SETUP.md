# TaskiT Development Setup

## Prerequisites

- Python 3.12
- Node.js and npm
- Redis if you want real Channels/worker behavior beyond basic local testing

## Backend

```bash
cd taskit-backend
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py create_test_users
python manage.py runserver
```

Backend runs at:

```text
http://127.0.0.1:8000
```

## Frontend

```bash
cd taskit-frontend
npm install
npm run dev -- --host 127.0.0.1
```

Frontend runs at:

```text
http://127.0.0.1:5173
```

## Mock Payments

For local payment testing without Pesapal sandbox calls, set this in `taskit-backend/.env`:

```env
PESAPAL_MOCK=True
```

## One Command Startup

From the repo root:

```bash
./start-dev.sh
```

This starts Django and Vite together. Stop both with `Ctrl+C`.
