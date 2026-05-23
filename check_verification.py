import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import User, UserVerification

for user in User.objects.all():
    try:
        v = user.verification
        print(f"User {user.email} has verification: {v.id}")
    except UserVerification.DoesNotExist:
        print(f"User {user.email} MISSING verification!")
