import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

from core.models import Institute, InstituteImage

def check_url(url):
    try:
        response = requests.head(url, timeout=5)
        # Cloudinary might return 200 for missing images if not configured to 404
        # but standard check is 200
        return response.status_code == 200
    except:
        return False

def fix_images():
    images = InstituteImage.objects.all()
    print(f"Checking {len(images)} institute images...")
    
    # Known working images (fallback list)
    valid_images = [
        'institute_photos/photo_DlFbnFR.jpg',
        'institute_photos/photo_GFJ2uFI.jpg',
        'institute_photos/photo_GQ7mqc4.jpg',
        'institute_photos/photo_GgPEOXc.jpg',
        'institute_photos/photo_GiKBfsP.jpg',
        'institute_photos/photo_I1ipCdE.jpg'
    ]
    
    fixed_count = 0
    for img in images:
        if img.image:
            try:
                url = img.image.url
                # If the URL is relative (local), make it absolute for checking
                if url.startswith('/'):
                    url = f"https://tapteacher.in{url}"
                
                print(f"Checking {img.institute.name}: {url}")
                if not check_url(url):
                    print(f"  FAILED: Broken image")
                    # Assign a valid image
                    img.image = valid_images[fixed_count % len(valid_images)]
                    img.save()
                    print(f"  FIXED: {img.image}")
                    fixed_count += 1
                else:
                    print(f"  OK")
            except Exception as e:
                print(f"  ERROR checking {img.institute.name}: {e}")
                img.image = valid_images[fixed_count % len(valid_images)]
                img.save()
                fixed_count += 1
        else:
            print(f"No image for {img.institute.name}, assigning default.")
            img.image = valid_images[fixed_count % len(valid_images)]
            img.save()
            fixed_count += 1

    print(f"Total fixed: {fixed_count}")

if __name__ == "__main__":
    fix_images()
