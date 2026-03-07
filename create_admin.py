import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tapteacher_project.settings")
django.setup()

from django.contrib.auth.models import User

try:
    if not User.objects.filter(username='pankajyadav5501@gmail.com').exists():
        User.objects.create_superuser('pankajyadav5501@gmail.com', 'pankajyadav5501@gmail.com', 'Pankaj@123')
        print("Superuser created successfully.")
    else:
        print("Superuser already exists.")
except Exception as e:
    print(f"Error: {e}")
