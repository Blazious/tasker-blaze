from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create verified JKUAT student test accounts for local development."

    def handle(self, *args, **options):
        User = get_user_model()
        test_users = [
            {
                "email": "alice.acheru@students.jkuat.ac.ke",
                "password": "Testpass123!",
                "full_name": "Alice Acheru",
                "phone_number": "+254700000001",
                "student_id": "SCT211-0001/2024",
                "department": "Computer Science",
                "year_of_study": 1,
            },
            {
                "email": "brian.otieno@students.jkuat.ac.ke",
                "password": "Testpass123!",
                "full_name": "Brian Otieno",
                "phone_number": "+254700000002",
                "student_id": "SCT211-0002/2023",
                "department": "Information Technology",
                "year_of_study": 2,
            },
            {
                "email": "cynthia.wanjiku@students.jkuat.ac.ke",
                "password": "Testpass123!",
                "full_name": "Cynthia Wanjiku",
                "phone_number": "+254700000003",
                "student_id": "SCT211-0003/2022",
                "department": "Software Engineering",
                "year_of_study": 3,
            },
        ]

        for user_data in test_users:
            password = user_data.pop("password")
            user, created = User.objects.get_or_create(
                email=user_data["email"],
                defaults={**user_data, "is_verified": True},
            )
            if created:
                user.set_password(password)
                user.full_clean()
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created {user.email}"))
            else:
                updated_fields = []
                for field, value in user_data.items():
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        updated_fields.append(field)
                if not user.is_verified:
                    user.is_verified = True
                    updated_fields.append("is_verified")
                if updated_fields:
                    user.full_clean()
                    user.save(update_fields=updated_fields)
                    self.stdout.write(self.style.WARNING(f"Updated {user.email}"))
                else:
                    self.stdout.write(f"Skipped {user.email}; already exists")
