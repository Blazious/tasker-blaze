from django.db.models import Count


PLATFORM_KNOWLEDGE = """
TaskiT is a JKUAT student marketplace for campus tasks. Current tagline: "Ingine Mwecheche."

Core platform areas:
- Human support: users can email TaskiT admin support directly at admintaskit@gmail.com. In the app, clicking the support email opens the user's email client with a new message.
- Auth: only @students.jkuat.ac.ke emails can register. Users verify email before posting tasks.
- KYC: students can upload front/back student ID and live face image. Mindee extracts ID details; face match can verify ownership.
- Tasks: clients post tasks with category, budget range, campus landmark, optional draggable map pin/current location, deadline, scheduled start, home-visit flag, and tasker gender preference.
- Categories: Laundry, Printing & Binding, Food Pickup, Errand Running, Thrifting, House Cleaning, House Hunting, Delivery, Tutoring, Other.
- Bids: taskers activate Tasker Mode, set availability, place one bid per open task, and cannot bid on their own task. Taskers with overdue TaskiT platform invoices cannot place new bids until settled.
- Chat: chat opens after a bid is accepted. It supports text, image attachments, voice notes/audio, typing indicators, safety cautions, quick replies, and task context.
- Payments: TaskiT has migrated from Pesapal to eConfirm. Do NOT say TaskiT currently uses Pesapal for active payments. The live flow is: client accepts bid, initiates eConfirm M-Pesa STK payment, eConfirm holds the agreed task amount in escrow, task becomes in progress after webhook/status sync, and client releases funds after confirming completion. eConfirm requires valid Kenyan mobile numbers and a minimum escrow amount of KES 100.
- Local payment sync: eConfirm cannot callback to localhost directly. In local development, TaskiT polls eConfirm status and has a DEBUG-only manual "I Already Paid" sync fallback. In production, use a public HTTPS eConfirm callback URL.
- Billing: TaskiT platform fees are post-paid, not deducted upfront from escrow. Taskers get the agreed task amount on release. TaskiT separately tracks a 10% platform fee after released paid tasks, waives usage during the 14-day trial, generates invoices with a 3-day grace period, and pauses bidding for overdue invoices. Users can view billing at /billing.
- Reviews: both parties review after completion. Reviews become visible only after both parties submit.
- Reports: users can report another account for harassment, safety issues, no-show, poor work, payment issues, inappropriate content, or other. Admins review reports.
- Notifications: users receive alerts for bids, accepted bids, payment, completed tasks, messages, reviews, and disputes.
- Safety: home visit warning, SOS call to Juja Police/Juja emergency numbers, WhatsApp location sharing with last-known fallback, hidden exact notes until assignment, dispute flow.
- Availability: taskers can be Available, Busy, or Offline. Clients can see this when choosing taskers.
- Scheduled tasks: clients can post ASAP tasks or schedule ahead for a future date/time.

Important policies:
- Do not advise users to move payment outside TaskiT.
- If asked about payments, explain eConfirm escrow and post-paid billing accurately. Do not mention Pesapal unless explaining an old/deprecated implementation.
- If asked about billing, direct users to /billing and explain trial, 10% tracking, invoice, 3-day grace period, and overdue bid blocking.
- For emergencies, tell users to use SOS/Juja police numbers or move to public safety first.
- For harassment, safety concerns, fraud, or unresolved disputes, escalate to admin support.
- If a user asks how to contact a human/admin/support directly, give admintaskit@gmail.com and say they can click the support email in the Help assistant to open their email client.
- If information is not known from TaskiT context or user state, say so and escalate.
- Answer in the same language the user used where possible, including Swahili or Sheng-style mixed English/Swahili.
"""


def build_user_context(user):
    from apps.payments.billing import billing_summary
    from apps.payments.models import Transaction
    from apps.tasks.models import Bid, Task

    posted_tasks = Task.objects.filter(client=user)
    assigned_tasks = Task.objects.filter(assigned_tasker=user)
    active_bids = Bid.objects.filter(tasker=user, status=Bid.Status.PENDING).count()
    open_tasks = posted_tasks.filter(status=Task.Status.OPEN).count()
    assigned_count = assigned_tasks.exclude(status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED]).count()
    released_count = Transaction.objects.filter(tasker=user, status=Transaction.Status.RELEASED).count()
    payment_counts = (
        Transaction.objects.filter(tasker=user)
        .values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )
    payment_summary = ", ".join(f"{row['status']}: {row['count']}" for row in payment_counts) or "none"
    billing = billing_summary(user)

    categories = (
        posted_tasks.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )
    status_summary = ", ".join(f"{row['status']}: {row['count']}" for row in categories) or "none"

    return f"""
Current user:
- Name: {user.full_name}
- Email: {user.email}
- Verified email: {user.is_verified}
- KYC verified: {user.is_kyc_verified}
- Tasker mode: {user.is_tasker_active}
- Availability: {getattr(user, 'availability_status', 'OFFLINE')}
- Department: {user.department or 'not set'}
- Posted tasks: {posted_tasks.count()} ({status_summary})
- Open posted tasks: {open_tasks}
- Active assignments as tasker: {assigned_count}
- Pending bids: {active_bids}
- Released paid tasks as tasker: {released_count}
- Tasker payment status summary: {payment_summary}
- Billing trial active: {billing['is_trial_active']}
- Billing trial ends at: {billing['trial_ends_at']}
- Current month platform fees due: KES {billing['current_month_due']}
- Overdue platform balance: KES {billing['overdue_balance']}
- Can place bids based on billing: {billing['can_bid']}
- Pending platform invoices: {len(billing['pending_invoices'])}
"""
