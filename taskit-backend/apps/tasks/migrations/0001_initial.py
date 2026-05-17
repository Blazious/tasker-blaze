import cloudinary.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("icon_name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name_plural": "task categories",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                ("description", models.TextField()),
                ("budget_min", models.DecimalField(decimal_places=2, max_digits=10)),
                ("budget_max", models.DecimalField(decimal_places=2, max_digits=10)),
                ("location_landmark", models.CharField(choices=[("Main Gate", "Main Gate"), ("Back Gate", "Back Gate"), ("Library", "Library"), ("Administration Block", "Administration Block"), ("Engineering Block", "Engineering Block"), ("ICT Centre", "ICT Centre"), ("Health Centre", "Health Centre"), ("Hostels Block A", "Hostels Block A"), ("Hostels Block B", "Hostels Block B"), ("Hostels Block C", "Hostels Block C"), ("Hostels Block D", "Hostels Block D"), ("Mess/Dining Hall", "Mess/Dining Hall"), ("Sports Ground", "Sports Ground"), ("JKUAT Town Stage", "JKUAT Town Stage"), ("Other (specify in notes)", "Other (specify in notes)")], max_length=100)),
                ("location_notes", models.CharField(blank=True, max_length=255)),
                ("task_photo", cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name="task_photo")),
                ("requires_home_visit", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("ASSIGNED", "Assigned"), ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled"), ("DISPUTED", "Disputed")], default="OPEN", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("deadline", models.DateTimeField(blank=True, null=True)),
                ("assigned_tasker", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_tasks", to=settings.AUTH_USER_MODEL)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tasks", to="tasks.taskcategory")),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="posted_tasks", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Bid",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("message", models.TextField()),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("REJECTED", "Rejected")], default="PENDING", max_length=20)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bids", to="tasks.task")),
                ("tasker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bids", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("task", "tasker")},
            },
        ),
    ]
