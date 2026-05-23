import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import EmailTemplate

def migrate_templates():
    admin_user = User.objects.filter(email='pankajyadav5501@gmail.com').first()
    if not admin_user:
        print("Admin user not found.")
        return
    
    templates = EmailTemplate.objects.filter(user__isnull=True)
    count = templates.update(user=admin_user)
    print(f"Assigned {count} templates to {admin_user.email}")

if __name__ == "__main__":
    migrate_templates()
