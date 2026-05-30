#!/usr/bin/env python
import os
import sys
import django

# Add the taskit-backend directory to the path
sys.path.insert(0, '/root/repo/taskit-backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

email = 'admintaskit@gmail.com'
username = 'admin'
password = 'admin123'  # Change this to a secure password

# Check if user already exists
if User.objects.filter(email=email).exists():
    print(f"Superuser with email {email} already exists.")
else:
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser created: {username} ({email})")

