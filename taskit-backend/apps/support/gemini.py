import json
import logging

import requests
from django.conf import settings

from .context import PLATFORM_KNOWLEDGE, build_user_context

logger = logging.getLogger(__name__)


class TaskitSupportBot:
    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        self.timeout = getattr(settings, "GEMINI_HTTP_TIMEOUT", 30)

    def answer(self, user, message, history=None):
        if not self.api_key:
            return self.fallback_answer(message)

        prompt = self.build_prompt(user, message, history or [])
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.35,
                "responseMimeType": "application/json",
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
            return {
                "answer": data.get("answer", "").strip(),
                "needs_escalation": bool(data.get("needs_escalation", False)),
                "ticket_title": data.get("ticket_title", "TaskiT support request"),
                "priority": data.get("priority", "NORMAL"),
            }
        except Exception as exc:
            logger.exception("Gemini support bot failed: %s", exc)
            fallback = self.fallback_answer(message)
            fallback["answer"] = (
                "I could not reach Gemini properly, so I am using TaskiT's built-in help mode. "
                + fallback["answer"]
            )
            return fallback

    def build_prompt(self, user, message, history):
        history_text = "\n".join(
            f"{item.sender}: {item.content[:500]}" for item in history[-8:]
        )
        return f"""
You are TaskiT Assistant, the in-app support chatbot for TaskiT.
You must answer only using platform knowledge and current user context.
If the user asks for something you cannot confidently answer, set needs_escalation=true.
If the issue involves safety, harassment, payment failure, fraud, account lockout, KYC rejection, or dispute, set needs_escalation=true.
Use the same language as the user where possible. Swahili is supported.

Return only JSON with:
{{
  "answer": "clear helpful answer",
  "needs_escalation": true or false,
  "ticket_title": "short admin ticket title if escalation is needed",
  "priority": "LOW, NORMAL, HIGH, or URGENT"
}}

Platform knowledge:
{PLATFORM_KNOWLEDGE}

User context:
{build_user_context(user)}

Recent chat:
{history_text or "No previous support messages."}

User question:
{message}
"""

    def fallback_answer(self, message):
        lower = message.lower()
        if any(word in lower for word in ["harass", "unsafe", "threat", "safety", "danger", "dhulumu", "hatari"]):
            return {
                "answer": "This sounds safety-related. Use SOS if you are in immediate danger, move to a public place if possible, and I will raise this for admin review.",
                "needs_escalation": True,
                "ticket_title": "Safety concern from support bot",
                "priority": "URGENT",
            }
        if any(word in lower for word in ["payment", "mpesa", "econfirm", "pay", "paid", "refund", "pesa", "escrow", "release", "stk"]):
            return {
                "answer": (
                    "Payments now use eConfirm escrow, not Pesapal. After a client accepts a bid, Pay Now sends an M-Pesa STK push using the client's profile phone number. "
                    "eConfirm holds the agreed task amount in escrow. When the task is done, the client approves completion and TaskiT triggers release to the tasker. "
                    "For local testing, TaskiT polls eConfirm because localhost callbacks are not reachable. eConfirm requires valid Kenyan mobile numbers and a minimum escrow of KES 100."
                ),
                "needs_escalation": False,
                "ticket_title": "Payment support request",
                "priority": "HIGH",
            }
        if any(word in lower for word in ["billing", "invoice", "fee", "trial", "grace", "owe", "balance", "billed"]):
            return {
                "answer": (
                    "TaskiT billing is post-paid. Taskers receive the agreed task amount from eConfirm, then TaskiT tracks a separate 10% platform fee after released paid tasks. "
                    "The first 14 days are a free trial, invoices have a 3-day grace period, and overdue invoices pause new bids. Open the Billing page from the navbar or go to /billing."
                ),
                "needs_escalation": False,
                "ticket_title": "Billing support request",
                "priority": "NORMAL",
            }
        if any(word in lower for word in ["bid", "bidding", "tasker", "availability", "offline", "online", "busy"]):
            return {
                "answer": (
                    "To bid, activate Tasker Mode, keep your availability updated, and open an available task. You cannot bid on your own task, on closed tasks, or while you have overdue platform invoices. "
                    "Clients can see whether taskers are Available, Busy, or Offline."
                ),
                "needs_escalation": False,
                "ticket_title": "Bidding support request",
                "priority": "NORMAL",
            }
        if any(word in lower for word in ["chat", "message", "voice", "audio", "image", "photo"]):
            return {
                "answer": (
                    "Chat opens after a bid is accepted. It supports text, image attachments, voice notes, typing indicators, quick replies, and task context. "
                    "Keep payment and important task changes inside TaskiT so support has a clear record."
                ),
                "needs_escalation": False,
                "ticket_title": "Chat support request",
                "priority": "NORMAL",
            }
        if any(word in lower for word in ["kyc", "id", "student id", "mindee", "verify", "verification", "ocr", "face"]):
            return {
                "answer": (
                    "KYC is in the profile section. Upload the front and back of your JKUAT student ID, then provide the live face capture. "
                    "Mindee OCR extracts student details and the face-match flow checks ownership. Extracted details can prefill profile fields."
                ),
                "needs_escalation": False,
                "ticket_title": "KYC support request",
                "priority": "NORMAL",
            }
        if any(word in lower for word in ["report", "review", "rating", "harassment", "complain", "complaint"]):
            return {
                "answer": (
                    "You can report a user from chat or their public profile. Reports go to TaskiT admins first, and only moderated concerns appear publicly. "
                    "Reviews are left after task completion and help future clients/taskers decide who to trust."
                ),
                "needs_escalation": "harassment" in lower,
                "ticket_title": "Report or review support request",
                "priority": "HIGH" if "harassment" in lower else "NORMAL",
            }
        if any(word in lower for word in ["house", "hunting", "bedsitter", "hostel", "room"]):
            return {
                "answer": "House Hunting is now one of the task categories. Use it when you need help finding hostels, bedsitters, rooms, or nearby student housing around JKUAT/Juja.",
                "needs_escalation": False,
                "ticket_title": "House hunting task support",
                "priority": "LOW",
            }
        return {
            "answer": "I can help with posting tasks, bidding, eConfirm escrow payments, post-paid billing, KYC, chat, reviews, reports, availability, scheduled tasks, House Hunting, and safety features. Ask me with a little more detail and I will guide you.",
            "needs_escalation": False,
            "ticket_title": "General support request",
            "priority": "NORMAL",
        }
