import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import Institute, InstituteImage
from django.conf import settings

def inspect_images():
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
    print(f"CLOUDINARY_URL in environ: {'CLOUDINARY_URL' in os.environ}")
    
    institutes = Institute.objects.filter(name__icontains="Swapnil")
    if not institutes.exists():
        print("Swapnil Public School not found.")
        # Try finding by district
        institutes = Institute.objects.filter(district__icontains="Nicobar")
    
    for inst in institutes:
        print(f"\nInstitute: {inst.name} (ID: {inst.id})")
        print(f"Location: {inst.district}, {inst.state}")
        images = inst.images.all()
        print(f"Images count: {len(images)}")
        for img in images:
            print(f"  - Image ID: {img.id}")
            print(f"    Path: {img.image}")
            try:
                print(f"    URL: {img.image.url}")
            except Exception as e:
                print(f"    URL Error: {e}")

if __name__ == "__main__":
    inspect_images()
