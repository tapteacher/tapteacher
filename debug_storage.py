import os
import django
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import get_raw_storage
from cloudinary_storage.storage import RawMediaCloudinaryStorage, MediaCloudinaryStorage

storage = get_raw_storage()
print(f"Storage: {type(storage)}")

if hasattr(storage, 'TAG'):
    print(f"Storage TAG: {storage.TAG}")

# Test PDF upload
file_content = b"fake pdf content %d" % os.getpid()
f = SimpleUploadedFile("mathematics_prt.pdf", file_content, content_type="application/pdf")

try:
    print("Uploading mathematics_prt.pdf...")
    name = storage.save("guidance/files/mathematics_prt.pdf", f)
    print(f"Saved name: {name}")
    url = storage.url(name)
    print(f"Generated URL: {url}")
    
    if "image/upload" in url:
        print("ALERT: URL contains 'image/upload'. This is likely WRONG for a raw file.")
    elif "raw/upload" in url:
        print("OK: URL contains 'raw/upload'.")
    else:
        print("UNKNOWN: URL format not recognized.")

except Exception as e:
    print(f"Upload failed: {e}")
