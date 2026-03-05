from app.config import settings
import os

print(f"Current working directory: {os.getcwd()}")
print(f"DATABASE_URL: {settings.DATABASE_URL}")
if settings.DATABASE_URL:
    print("Verification SUCCESS: DATABASE_URL is loaded.")
else:
    print("Verification FAILED: DATABASE_URL is still None.")
