from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0002_seed_task_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="preferred_tasker_gender",
            field=models.CharField(
                choices=[
                    ("ANY", "Any"),
                    ("FEMALE", "Female"),
                    ("MALE", "Male"),
                ],
                default="ANY",
                max_length=10,
            ),
        ),
    ]
