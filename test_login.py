import os
import django
import sys

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tapteacher_project.settings")
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
c = Client()
try:
    response = c.post('/login/', {'username': 'pankajyadav5501@gmail.com', 'password': 'Pankaj@123'}, follow=True)
    print("Login status (followed):", response.status_code)
    if response.status_code == 500:
        print("500 response content:")
        print(response.content.decode('utf-8'))
except Exception as e:
    import traceback
    traceback.print_exc()

print("\n--- Testing Google Login Callback ---\n")
try:
    response = c.post('/google-login/', {'credential': 'fake_token', 'email': 'pankajyadav5501@gmail.com'}, follow=True)
    print("Google callback status (followed):", response.status_code)
    if response.status_code == 500:
        print(response.content)
except Exception as e:
    import traceback
    traceback.print_exc()
