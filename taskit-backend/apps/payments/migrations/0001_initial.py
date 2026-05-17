from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0002_seed_task_categories"),
    ]

    operations = [
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("agreed_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("platform_fee", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("tasker_payout", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("total_charged", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("status", models.CharField(choices=[("PENDING_PAYMENT", "Pending Payment"), ("ESCROWED", "Escrowed"), ("RELEASED", "Released"), ("REFUNDED", "Refunded"), ("DISPUTED", "Disputed")], default="PENDING_PAYMENT", max_length=20)),
                ("pesapal_order_id", models.CharField(blank=True, max_length=255)),
                ("pesapal_tracking_id", models.CharField(blank=True, max_length=255)),
                ("payment_method", models.CharField(blank=True, max_length=100)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("released_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payment_transactions", to=settings.AUTH_USER_MODEL)),
                ("task", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="transaction", to="tasks.task")),
                ("tasker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="earning_transactions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="EscrowLedger",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("HOLD", "Hold"), ("RELEASE", "Release"), ("REFUND", "Refund"), ("FEE_COLLECTED", "Fee Collected")], max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("transaction", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to="payments.transaction")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DisputeNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(max_length=255)),
                ("details", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("raised_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raised_disputes", to=settings.AUTH_USER_MODEL)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dispute_notes", to="tasks.task")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
