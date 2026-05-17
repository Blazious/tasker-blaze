from django.db import migrations


def add_house_hunting_category(apps, schema_editor):
    TaskCategory = apps.get_model("tasks", "TaskCategory")
    TaskCategory.objects.update_or_create(
        slug="house-hunting",
        defaults={
            "name": "House Hunting",
            "icon_name": "home",
            "description": "Help finding hostels, bedsitters, rooms, and nearby student housing.",
            "is_active": True,
        },
    )


def remove_house_hunting_category(apps, schema_editor):
    TaskCategory = apps.get_model("tasks", "TaskCategory")
    TaskCategory.objects.filter(slug="house-hunting").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0005_task_schedule_type_task_scheduled_for"),
    ]

    operations = [
        migrations.RunPython(add_house_hunting_category, remove_house_hunting_category),
    ]
