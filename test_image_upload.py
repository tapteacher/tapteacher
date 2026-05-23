import os
import django
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

import cloudinary.uploader
from cloudinary_storage.storage import MediaCloudinaryStorage

storage = MediaCloudinaryStorage()
print("Storage class:", type(storage))

file_content = b"fake image content"
f = SimpleUploadedFile("test.png", file_content, content_type="image/png")

try:
    print("Trying to save image file to storage...")
    name = storage.save("guidance/images/test.png", f)
    print("Success! File saved as:", name)
except Exception as e:
    print("Error during upload:")
    import traceback
    traceback.print_exc()
