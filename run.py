"""
run.py — Quick start script
Run this to check your setup and start the backend server.

Usage:  python run.py
"""

import os
import sys
import subprocess

print("""
╔══════════════════════════════════════════════════════════╗
║          SecureVault — Cloud Storage Project             ║
║              CS-308 Cloud Computing                      ║
╚══════════════════════════════════════════════════════════╝
""")

# Check .env exists
if not os.path.exists(".env"):
    print("⚠  No .env file found!")
    print("   Copy .env.example to .env and fill in your AWS values.\n")
    sys.exit(1)
else:
    print("✅ .env file found")

# Check Python packages
try:
    import flask
    import boto3
    import cryptography
    print("✅ Python packages installed")
except ImportError as e:
    print(f"❌ Missing package: {e}")
    print("   Run: pip install -r backend/requirements.txt -r security/requirements.txt -r storage/requirements.txt")
    sys.exit(1)

# Check .env values
from dotenv import load_dotenv
load_dotenv()

missing = []
for var in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "KMS_KEY_ID",
            "S3_BUCKET_PRIMARY", "S3_BUCKET_SECONDARY", "DYNAMODB_TABLE"]:
    val = os.getenv(var, "")
    if not val or "your_" in val or "xxxxxxxxx" in val:
        missing.append(var)

if missing:
    print(f"\n⚠  These .env variables are not set yet:")
    for m in missing:
        print(f"   - {m}")
    print("\n   The server will start but AWS calls will fail until you set these.")
    print("   For now you can still test the frontend in DEV MODE (no AWS needed).\n")
else:
    print("✅ AWS environment variables set")

print("\n🚀 Starting Flask API on http://localhost:5000 ...")
print("   Press Ctrl+C to stop.\n")
print("   In a separate terminal, start the frontend:")
print("     cd frontend")
print("     npm install")
print("     npm start")
print("   Then open: http://localhost:3000\n")
print("─" * 55)

# Start the Flask server
os.environ["PYTHONPATH"] = os.getcwd()
subprocess.run([sys.executable, "-m", "backend.app"])