import os
import django
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

import cloudinary.uploader
from core.models import get_raw_storage

storage = get_raw_storage()
print("Storage class:", type(storage))

file_content = b"fake pdf content"
f = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")

try:
    print("Trying to save file to storage...")
    name = storage.save("guidance/pdfs/test.pdf", f)
    print("Success! File saved as:", name)
    print("File URL:", storage.url(name))
except Exception as e:
    print("Error during upload:")
    import traceback
    traceback.print_exc()
