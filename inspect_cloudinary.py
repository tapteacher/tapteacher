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

public_id = "media/guidance/files/mathematics_prt_dzdfnf.pdf"

try:
    print(f"Inspecting public_id: {public_id}")
    resource = cloudinary.api.resource(public_id, resource_type="raw")
    print("\nResource Metadata:")
    for k, v in resource.items():
        if k != 'derived':
            print(f"  {k}: {v}")
    
    print("\nURL from metadata:", resource.get('url'))
    print("Secure URL from metadata:", resource.get('secure_url'))
    print("Access Mode:", resource.get('access_mode'))
    print("Type:", resource.get('type'))

except Exception as e:
    print(f"Error fetching resource metadata: {e}")
