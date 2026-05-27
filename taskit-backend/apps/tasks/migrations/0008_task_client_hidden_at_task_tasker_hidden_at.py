from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0007_task_tasker_completed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="client_hidden_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="tasker_hidden_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
