from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0006_add_house_hunting_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="tasker_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
