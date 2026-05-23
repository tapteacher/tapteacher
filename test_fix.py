import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserVerification
from core.views import save_location_preference
from django.test import RequestFactory

def test_save_pref_no_profile():
    # 1. Create a fresh user
    username = "testuser_fix"
    email = "testuser_fix@example.com"
    User.objects.filter(email=email).delete()
    user = User.objects.create_user(username=username, email=email, password="password123")
    
    # Ensure verification object is NOT created if signals were disabled (simulating missing profile)
    # But signals should create it. Let's delete it if it exists.
    UserVerification.objects.filter(user=user).delete()
    
    print(f"User created. Verification exists: {UserVerification.objects.filter(user=user).exists()}")
    
    # 2. Mock request to save_location_preference
    factory = RequestFactory()
    data = {
        'state': 'Uttar Pradesh',
        'district': 'Lucknow',
        'categories': ['govt', 'private'],
        'subjects': {'PRT': ['Maths'], 'TGT': [], 'PGT': [], 'Others': []}
    }
    request = factory.post('/api/save-location-preference/', 
                          data=json.dumps(data), 
                          content_type='application/json')
    request.user = user
    request.session = {}
    
    # 3. Call the view
    response = save_location_preference(request)
    
    print(f"Response: {response.content.decode()}")
    
    # 4. Verify DB
    v = UserVerification.objects.get(user=user)
    print(f"Verification created: {v.id}")
    print(f"Prefs saved: {v.location_preferences}")
    
    if v.location_preferences and v.location_preferences[0]['state'] == 'Uttar Pradesh':
        print("TEST PASSED: Location saved successfully without prior profile save.")
    else:
        print("TEST FAILED.")

if __name__ == "__main__":
    test_save_pref_no_profile()
