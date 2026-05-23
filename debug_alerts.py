import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import VacancyPost, UserVerification
from django.utils import timezone
from datetime import timedelta
import json

print("\n--- NEW VACANCIES STRINGS---")
time_threshold = timezone.now() - timedelta(minutes=60)
new_posts = VacancyPost.objects.filter(
    # vacancy__created_at__lte=time_threshold,
    vacancy__is_active=True,
    alert_emails_sent=False
).select_related('vacancy', 'vacancy__institute')

for post in new_posts:
    print(f"ID: {post.id}")
    print(f"State: '{post.vacancy.institute.state}'")
    print(f"District: '{post.vacancy.institute.district}'")
    print(f"Category: '{post.category}'")
    print(f"Subject: '{post.subject}'")
    print(f"State length: {len(post.vacancy.institute.state)}")
    print(f"District length: {len(post.vacancy.institute.district)}")
    print("-" * 20)

print("\n--- USER PREFERENCES STRINGS ---")
for verif in UserVerification.objects.prefetch_related('user'):
    print(f"User: {verif.user.email}")
    prefs = verif.location_preferences
    print(json.dumps(prefs, indent=2))
    print("=" * 30)
