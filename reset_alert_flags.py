import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import VacancyPost
print("Resetting alert_emails_sent for all active vacancies...")
count = VacancyPost.objects.filter(vacancy__is_active=True).update(alert_emails_sent=False)
print(f"Reset {count} posts. Ready for re-test.")
