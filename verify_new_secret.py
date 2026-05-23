import os
import cloudinary
import cloudinary.api
from dotenv import load_dotenv

load_dotenv()

cloudinary_url = os.environ.get('CLOUDINARY_URL')
print(f"Testing CLOUDINARY_URL: {cloudinary_url}")

try:
    # Explicitly configure to be sure
    cloudinary.config(
        cloud_name="dflmqkl6o",
        api_key="829762746427825",
        api_secret="22m1XJz0q6N31FlgGjfgVbs1V2c"
    )
    
    # Try a simple API call that requires authentication
    res = cloudinary.api.ping()
    print("SUCCESS: Cloudinary Ping matched with INDIVIDUAL PARAMS!")
except Exception as e:
    print(f"FAILED: Cloudinary Auth Error: {e}")
