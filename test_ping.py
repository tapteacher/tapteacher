import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

import cloudinary
import cloudinary.api

try:
    print("Pinging Cloudinary...")
    res = cloudinary.api.ping()
    print("Ping response:", res)
except Exception as e:
    print("Error pinging Cloudinary:", str(e))
