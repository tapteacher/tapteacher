import os
import django
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import GuidanceCategory, GuidanceSubject, GuidanceTopic, GuidanceTopicFile

cat, _ = GuidanceCategory.objects.get_or_create(slug='test', name='TEST')
sub, _ = GuidanceSubject.objects.get_or_create(category=cat, name='Test Subject')
topic = GuidanceTopic.objects.create(subject=sub, title='Test Topic', is_for_everyone=True)

file_content = b"fake pdf content"
f = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")

try:
    obj = GuidanceTopicFile.objects.create(topic=topic, file=f, file_type='pdf')
    print("Success! File saved at:", obj.file.name)
except Exception as e:
    print("Error during upload:")
    import traceback
    traceback.print_exc()
