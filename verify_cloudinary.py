import os
import cloudinary
import cloudinary.api
from dotenv import load_dotenv

load_dotenv()

cloudinary_url = "cloudinary://829762746427825:rE7-jEqjJ99wQY9i15H_t9yK890@dflmqk16o"
print(f"Testing CLOUDINARY_URL: {cloudinary_url}")

try:
    # Explicitly configure to be sure
    cloudinary.config(
        cloudinary_url=cloudinary_url
    )
    
    # Try a simple API call that requires authentication
    res = cloudinary.api.ping()
    print("SUCCESS: Cloudinary Ping matched!")
except Exception as e:
    print(f"FAILED: Cloudinary Auth Error: {e}")
