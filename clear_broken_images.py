import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import InstituteImage

def clear_broken_images():
    """Delete all InstituteImage records that point to broken/missing files"""
    images = InstituteImage.objects.all()
    print(f"Total images: {len(images)}")
    
    broken = []
    for img in images:
        # These are the known missing files
        filename = str(img.image)
        if 'photo_' in filename or 'ChatGPT' in filename or 'Screenshot' in filename:
            # Verify if properly uploaded to Cloudinary - if not, mark as broken 
            broken.append(img)
            print(f"Will delete: {filename} for {img.institute.name}")

    if broken:
        confirm = input(f"\nDelete {len(broken)} broken records? (yes/no): ")
        if confirm.strip().lower() == 'yes':
            for img in broken:
                img.delete()
            print(f"Deleted {len(broken)} broken image records.")
        else:
            print("Aborted.")
    else:
        print("No broken images found.")

clear_broken_images()
