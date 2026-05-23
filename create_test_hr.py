import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import User, AdminRole

email = 'hr@example.com'
user, created = User.objects.get_or_create(email=email, defaults={'username': 'hr_test'})
user.set_password('hr123')
user.is_staff = True
user.save()

# Give HR some roles
admin_role, _ = AdminRole.objects.get_or_create(user=user)
admin_role.roles = ['upload_vacancy', 'submitted_vacancies']
admin_role.save()

print(f"Test HR created: {email} / hr123")
