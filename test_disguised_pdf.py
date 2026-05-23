import os
import django
import cloudinary
import cloudinary.uploader

# Hardcoded for debugging
cloudinary.config(
    cloud_name="dflmqkl6o",
    api_key="829762746427825",
    api_secret="22m1XJz0q6N31FlgGjfgVbs1V2c"
)

# Tiny PDF content
pdf_data = b'%PDF-1.1\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>endobj\n4 0 obj<</Length 21>>stream\nBT /F1 12 Tf ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\n0000000178 00000 n\ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n249\n%%EOF'

try:
    print("Uploading PDF disguised as JPG...")
    # Cloudinary usually ignores the extension in the upload call and looks at the file,
    # but let's see what happens if we force the public_id to have .jpg
    result = cloudinary.uploader.upload(pdf_data, public_id="test_disguised_pdf.jpg", resource_type="image")
    print("Upload Result:")
    print(f"  URL: {result.get('url')}")
    print(f"  Format: {result.get('format')}")
    
    # Check if we can access it
except Exception as e:
    print(f"Upload failed: {e}")
