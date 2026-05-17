# TaskiT

**Ingine Mwecheche.**

TaskiT is a JKUAT student marketplace for campus errands and services. Students can post tasks, bid as taskers, chat after assignment, fund work through eConfirm escrow, release payment after completion, review each other, report safety issues, complete lightweight KYC, and use a TaskiT assistant chatbot for platform help.

## What It Includes

- Student-only auth using `@students.jkuat.ac.ke` emails and JWT sessions.
- Task posting with categories, budgets, campus landmarks, map pins, deadlines, scheduled tasks, home-visit warnings, and tasker gender preference.
- Task categories including Laundry, Printing & Binding, Food Pickup, Errand Running, Thrifting, House Cleaning, House Hunting, Delivery, Tutoring, and Other.
- Tasker mode with availability states: Available, Busy, and Offline.
- Bidding, bid acceptance, assigned-task workflow, and task completion.
- eConfirm escrow payments with M-Pesa STK push using phone numbers from user profiles.
- Post-paid platform billing: 14-day trial, 10% tracked platform fee, monthly invoice view, and 3-day grace period.
- Real-time chat with text, image attachments, voice notes, typing indicators, task context, and safety cautions.
- Notifications for bids, accepted bids, payment, completion, reviews, disputes, and messages.
- Lightweight KYC in profile using Mindee OCR fields and face-match placeholders.
- Reports and reviews so users can raise concerns beyond star ratings.
- SOS and WhatsApp location sharing safety tools.
- TaskiT Assistant powered by Gemini 2.5 Flash when configured.

## Project Structure

```text
tasker/
  taskit-backend/     Django REST API, Channels, payments, KYC, chat, billing
  taskit-frontend/    React + Vite frontend
  README.md           This file
  SETUP.md            Older quick setup notes
  start-dev.sh        Bash helper to start backend and frontend together
```

## Requirements

- Python 3.12
- Node.js and npm
- Redis for real-time chat/Channels
- Optional Docker for running Redis quickly
- eConfirm API key for live escrow payments
- Gemini API key for the chatbot
- Mindee credentials for OCR/KYC
- Cloudinary credentials if uploading media to Cloudinary

## Backend Setup

From the project root:

```powershell
cd taskit-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py create_test_users
python manage.py runserver
```

The backend runs at:

```text
http://127.0.0.1:8000
```

The API base URL is:

```text
http://127.0.0.1:8000/api/v1/
```

## Frontend Setup

In a second terminal:

```powershell
cd taskit-frontend
npm install
npm run dev -- --host 127.0.0.1
```

The frontend runs at:

```text
http://127.0.0.1:5173
```

## Redis for Chat

If you have Docker:

```powershell
docker run --name taskit-redis -p 6379:6379 -d redis:7
```

If the container already exists:

```powershell
docker start taskit-redis
```

The backend expects:

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

## Environment Variables

Copy `taskit-backend/.env.example` to `taskit-backend/.env`, then fill in values as needed.

Important variables:

```env
SECRET_KEY=replace-this-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://127.0.0.1:6379/0

ECONFIRM_API_KEY=
ECONFIRM_BASE_URL=https://econfirm.co.ke/api/v1
ECONFIRM_CALLBACK_URL=http://localhost:8000/api/v1/payments/econfirm-callback/
ECONFIRM_MOCK=False
PLATFORM_FEE_PERCENT=10

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

KYC_MOCK=True
MINDEE_API_KEY=
MINDEE_ENDPOINT_URL=
```

Do not commit real API keys.

## eConfirm Payments

Payment flow:

1. Client accepts a bid.
2. Client clicks Pay Now.
3. TaskiT creates an eConfirm escrow using the client and tasker profile details.
4. TaskiT initiates M-Pesa STK push using the client's profile phone number.
5. eConfirm holds the agreed task amount in escrow.
6. TaskiT marks the task as in progress when eConfirm reports the escrow as funded.
7. After the task is complete, the client clicks release.
8. TaskiT calls eConfirm release so the tasker receives the payout.
9. TaskiT tracks the platform fee separately for post-paid billing.

For local development, eConfirm cannot call `localhost` directly. The frontend polls payment status automatically while a payment is pending. For true webhook callbacks, expose Django with HTTPS using a tunnel such as ngrok and update:

```env
ECONFIRM_CALLBACK_URL=https://your-ngrok-url/api/v1/payments/econfirm-callback/
```

## Billing

TaskiT uses a post-paid platform fee model:

- 14-day free trial from user signup.
- During trial, completed task volume is tracked but the platform fee is waived.
- After trial, TaskiT tracks a 10% platform fee on released paid tasks.
- Billing is visible at `/billing`.
- Invoices have a 3-day grace period.
- Overdue taskers are blocked from placing new bids.

## KYC

KYC lives in the profile area. The intended workflow:

- Upload front of student ID.
- Upload back of student ID.
- Extract student details using Mindee OCR.
- Detect ID photo and JKUAT stamp.
- Compare ID photo with live face capture using face matching.
- Prefill profile fields where OCR data is available.

For local testing, `KYC_MOCK=True` can keep the flow usable without full OCR/face model setup.

## Chat

Chat opens after a task is assigned. It supports:

- Real-time websocket messaging through Django Channels and Redis.
- REST fallback/sync.
- Text messages.
- Image attachments.
- Voice notes.
- Typing indicators.
- Task context header.
- Quick replies.
- Safety caution copy.

## Useful Commands

Backend checks and tests:

```powershell
cd taskit-backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Payment tests:

```powershell
.\.venv\Scripts\python.exe manage.py test apps.payments
```

Frontend build:

```powershell
cd taskit-frontend
npm run build
```

## Common Local Workflow

1. Start Redis.
2. Start Django backend.
3. Start Vite frontend.
4. Log in with a verified student account.
5. Post a task.
6. Log in as a tasker and place a bid.
7. Accept the bid as the client.
8. Pay through eConfirm STK.
9. Wait for automatic status sync or webhook.
10. Release payment after completion.
11. Review/report if needed.
12. Check `/billing` for tracked platform fees.

## Notes

- eConfirm live API requires valid Kenyan mobile phone numbers on user profiles.
- eConfirm currently requires a minimum escrow amount of KES 100.
- Local manual escrow confirmation is development-only and guarded by `DEBUG=True`.
- Use HTTPS callback URLs for real webhook testing.
