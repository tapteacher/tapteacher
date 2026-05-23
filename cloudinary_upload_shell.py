import os
import sys

photo_dir = 'media/institute_photos'
files_to_upload = [
    'photo_DlFbnFR.jpg',
    'photo_GFJ2uFI.jpg',
    'photo_GQ7mqc4.jpg',
    'photo_GgPEOXc.jpg',
    'photo_GiKBfsP.jpg',
    'photo_I1ipCdE.jpg',
]

for filename in files_to_upload:
    local_path = os.path.join(photo_dir, filename)
    if os.path.exists(local_path):
        public_id = f'institute_photos/{os.path.splitext(filename)[0]}'
        print(f"Uploading {local_path} -> {public_id} ...")
        import cloudinary.uploader
        result = cloudinary.uploader.upload(
            local_path,
            public_id=public_id,
            overwrite=True,
            resource_type='image'
        )
        print(f"  Uploaded: {result['secure_url']}")
    else:
        print(f"  File not found locally: {local_path}")

print("Done!")
