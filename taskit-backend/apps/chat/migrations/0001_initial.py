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
            name="ChatThread",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("participants", models.ManyToManyField(related_name="chat_threads", to=settings.AUTH_USER_MODEL)),
                ("task", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="chat_thread", to="tasks.task")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("is_read", models.BooleanField(default=False)),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_messages", to=settings.AUTH_USER_MODEL)),
                ("thread", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chat.chatthread")),
            ],
            options={
                "ordering": ["timestamp"],
            },
        ),
    ]
