import os
import django
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

import cloudinary.uploader
from cloudinary_storage.storage import MediaCloudinaryStorage

storage = MediaCloudinaryStorage()

file_content = b"fake image content"
# Test with a filename that has spaces, like the one in the user's screenshot ("Mar 14, 2026, 05 19 11 AM.jpg")
f = SimpleUploadedFile("Mar 14, 2026, 05 19 11 AM.jpg", file_content, content_type="image/jpeg")

try:
    print("Trying to save spaced filename to storage...")
    name = storage.save("guidance/images/Mar 14, 2026, 05 19 11 AM.jpg", f)
    print("Success! File saved as:", name)
except Exception as e:
    print("Error during upload:", str(e))
    # import traceback
    # traceback.print_exc()

# Test with a clean filename
f2 = SimpleUploadedFile("clean_filename.jpg", file_content, content_type="image/jpeg")
try:
    print("\nTrying to save clean filename to storage...")
    name2 = storage.save("guidance/images/clean_filename.jpg", f2)
    print("Success! File saved as:", name2)
except Exception as e:
    print("Error during upload:", str(e))

