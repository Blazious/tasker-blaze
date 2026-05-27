from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("payments", "0003_platforminvoice_platformfeeusage"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlatformInvoicePayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("provider", models.CharField(default="INTASEND", max_length=50)),
                ("api_ref", models.CharField(max_length=120, unique=True)),
                ("provider_invoice_id", models.CharField(blank=True, max_length=120)),
                ("checkout_id", models.CharField(blank=True, max_length=120)),
                ("phone_number", models.CharField(blank=True, max_length=32)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PROCESSING", "Processing"), ("PAID", "Paid"), ("FAILED", "Failed")], default="PENDING", max_length=20)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("raw_callback", models.JSONField(blank=True, default=dict)),
                ("failure_reason", models.TextField(blank=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="payments.platforminvoice")),
                ("tasker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="platform_invoice_payments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
