import os
import django
import cloudinary
import cloudinary.uploader
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

# Hardcoded for debugging
cloudinary.config(
    cloud_name="dflmqkl6o",
    api_key="829762746427825",
    api_secret="22m1XJz0q6N31FlgGjfgVbs1V2c"
)

# Tiny transparent 1x1 GIF
img_data = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'

try:
    print("Uploading test image...")
    result = cloudinary.uploader.upload(img_data, public_id="test_image_access", resource_type="image")
    print("Upload Result:")
    print(f"  URL: {result.get('url')}")
    print(f"  Secure URL: {result.get('secure_url')}")
    
    url = result.get('secure_url')
    print(f"\nNow checking access to {url}...")
    
    # We'll use curl from the shell after this
except Exception as e:
    print(f"Upload failed: {e}")
