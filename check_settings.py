import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from django.conf import settings
print("USE_CLOUDINARY:", settings.USE_CLOUDINARY)
if hasattr(settings, 'CLOUDINARY_URL') or 'CLOUDINARY_URL' in os.environ:
    print("CLOUDINARY_URL is set.")
else:
    print("CLOUDINARY_URL is NOT set.")
