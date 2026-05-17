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
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notification_type", models.CharField(choices=[("NEW_BID", "New Bid"), ("BID_ACCEPTED", "Bid Accepted"), ("PAYMENT_RECEIVED", "Payment Received"), ("TASK_COMPLETED", "Task Completed"), ("NEW_MESSAGE", "New Message"), ("REVIEW_RECEIVED", "Review Received"), ("TASK_DISPUTED", "Task Disputed")], max_length=30)),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
                ("related_task", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notifications", to="tasks.task")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
