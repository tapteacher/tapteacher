import hashlib
import time

def generate_signature(params, api_secret):
    # Sort parameters alphabetically
    sorted_params = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    # Append secret and hash
    return hashlib.sha1((sorted_params + api_secret).encode('utf-8')).hexdigest()

# From the screenshot (Step 288)
string_to_sign = "folder=media/guidance/files&tags=media&timestamp=1773461521&use_filename=1"
expected_signature = "ed5397ff2ea83019c82fec5deddb4299179d1c9a" # From the screenshot text

# My transcribed secret
api_secret = "rE7-jEqjJ99wQY9i15H_t9yK890"

# Note: The "string to sign" in Cloudinary is already sorted and formatted.
# So we just append the secret to that exact string.
actual_signature = hashlib.sha1((string_to_sign + api_secret).encode('utf-8')).hexdigest()

print(f"String to sign: {string_to_sign}")
print(f"Expected signature: {expected_signature}")
print(f"Calculated signature: {actual_signature}")

if actual_signature == expected_signature:
    print("MATCH! The API Secret is correct.")
else:
    print("MISMATCH! The API Secret is still wrong.")
