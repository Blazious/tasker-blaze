import cloudinary.models
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("full_name", models.CharField(max_length=255)),
                ("phone_number", models.CharField(max_length=32)),
                ("student_id", models.CharField(blank=True, max_length=64)),
                ("department", models.CharField(blank=True, max_length=255)),
                ("year_of_study", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("profile_photo", cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name="profile_photo")),
                ("bio", models.TextField(blank=True)),
                ("is_tasker_active", models.BooleanField(default=False)),
                ("is_verified", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen", models.DateTimeField(blank=True, null=True)),
                ("groups", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={
                "ordering": ["-date_joined"],
            },
        ),
    ]
