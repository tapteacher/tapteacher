import os
import django
import cloudinary
import cloudinary.api

# Hardcoded for debugging
cloudinary.config(
    cloud_name="dflmqkl6o",
    api_key="829762746427825",
    api_secret="22m1XJz0q6N31FlgGjfgVbs1V2c"
)

# New ID based on user screenshot: mathematics_prt_ghlp80.pdf
# We try both ID with and without extension
ids_to_try = [
    ("media/guidance/files/mathematics_prt_ghlp80", "image"),
    ("media/guidance/files/mathematics_prt_ghlp80.pdf", "image"),
    ("media/guidance/files/mathematics_prt_ghlp80.pdf", "raw")
]

for pid, rtype in ids_to_try:
    print(f"\n--- Trying pid: {pid}, type: {rtype} ---")
    try:
        resource = cloudinary.api.resource(pid, resource_type=rtype)
        print("SUCCESS!")
        print(f"  Public ID: {resource.get('public_id')}")
        print(f"  Type: {resource.get('type')}")
        print(f"  Access Mode: {resource.get('access_mode')}")
        print(f"  Secure URL: {resource.get('secure_url')}")
    except Exception as e:
        print(f"Failed: {e}")
