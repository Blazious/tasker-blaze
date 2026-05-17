from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0002_seed_task_categories"),
    ]

    operations = [
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("comment", models.TextField(max_length=500)),
                ("review_type", models.CharField(choices=[("CLIENT_TO_TASKER", "Client to Tasker"), ("TASKER_TO_CLIENT", "Tasker to Client")], max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_visible", models.BooleanField(default=False)),
                ("reviewee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews_received", to=settings.AUTH_USER_MODEL)),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews_written", to=settings.AUTH_USER_MODEL)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="tasks.task")),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("task", "reviewer")},
            },
        ),
    ]
