from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser for the application'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='admintaskit@gmail.com', help='Email for the superuser')
        parser.add_argument('--username', type=str, default='admin', help='Username for the superuser')
        parser.add_argument('--password', type=str, default='admin123', help='Password for the superuser')

    def handle(self, *args, **options):
        email = options['email']
        username = options['username']
        password = options['password']

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Superuser with email {email} already exists.'))
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Superuser created: {username} ({email})'))

