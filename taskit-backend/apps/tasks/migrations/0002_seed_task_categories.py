from django.db import migrations


CATEGORIES = [
    ("Laundry", "laundry", "washing-machine", "Laundry and clothes care errands."),
    ("Printing & Binding", "printing-binding", "printer", "Printing, photocopying, and binding jobs."),
    ("Food Pickup", "food-pickup", "utensils", "Food collection and pickup tasks."),
    ("Errand Running", "errand-running", "map", "General campus errands."),
    ("Thrifting", "thrifting", "shirt", "Thrift shopping and item sourcing."),
    ("House Cleaning", "house-cleaning", "sparkles", "Room, hostel, and house cleaning tasks."),
    ("Delivery", "delivery", "package", "Campus and nearby delivery tasks."),
    ("Tutoring", "tutoring", "graduation-cap", "Academic tutoring and study support."),
    ("Other", "other", "circle-ellipsis", "Tasks that do not fit another category."),
]


def seed_categories(apps, schema_editor):
    TaskCategory = apps.get_model("tasks", "TaskCategory")
    for name, slug, icon_name, description in CATEGORIES:
        TaskCategory.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "icon_name": icon_name,
                "description": description,
                "is_active": True,
            },
        )


def remove_categories(apps, schema_editor):
    TaskCategory = apps.get_model("tasks", "TaskCategory")
    TaskCategory.objects.filter(slug__in=[category[1] for category in CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_categories),
    ]
