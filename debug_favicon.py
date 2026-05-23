import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import SiteSettings

def inspect_settings():
    s = SiteSettings.objects.first()
    if s:
        print(f"YouTube: {s.youtube_link}")
        print(f"Telegram: {s.telegram_link}")
        # Check if there are any other fields we missed
        for field in s._meta.fields:
            if field.name not in ['id', 'youtube_link', 'telegram_link']:
                print(f"{field.name}: {getattr(s, field.name)}")
    else:
        print("No SiteSettings found.")

if __name__ == "__main__":
    inspect_settings()
