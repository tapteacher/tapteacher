import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import Vacancy, User

admin_email = 'pankajyadav5501@gmail.com'
admin_user, created = User.objects.get_or_create(email=admin_email, defaults={'username': 'pankajyadav5501'})
if created:
    print(f"Created admin user {admin_email}")

updated_count = Vacancy.objects.filter(uploaded_by__isnull=True).update(uploaded_by=admin_user)
print(f"Assigned {updated_count} existing vacancies to {admin_email}")
