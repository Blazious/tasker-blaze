from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="gender",
            field=models.CharField(
                choices=[
                    ("NOT_SPECIFIED", "Prefer not to say"),
                    ("FEMALE", "Female"),
                    ("MALE", "Male"),
                    ("OTHER", "Other"),
                ],
                default="NOT_SPECIFIED",
                max_length=20,
            ),
        ),
    ]
