"""
backend/app.py
==============
ABDULLAH WAHEED — Backend API (Coordinator)

This is the central Flask REST API that connects:
- Arfah's security/encrypt.py  (encryption)
- Anila's storage/shard_manager.py (S3 storage)
- database.py (DynamoDB)

All requests from the React frontend come here first.

API Endpoints:
  POST   /api/upload          — Upload and encrypt a file
  GET    /api/files           — List all files for current user
  GET    /api/download/<id>   — Download and decrypt a file
  DELETE /api/files/<id>      — Delete a file
  GET    /api/health          — S3 bucket health status
  GET    /api/ping            — Check if server is running

Authentication:
  Every request (except /ping) requires an Authorization header:
  Authorization: Bearer <cognito_jwt_token>
  The token is verified using AWS Cognito's public keys.
"""

import os
import sys
import uuid
import json
import io

# Make sure we can import from sibling folders
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

# Import our modules
from security.encrypt   import encrypt_file, decrypt_file
from storage.shard_manager import upload_shards, download_shards, delete_file_shards, check_bucket_health
from backend.database   import save_file_record, get_file_record, list_user_files, delete_file_record
from backend.auth       import verify_token, get_user_id_from_token

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow React frontend


# ── Helper: Get Current User ──────────────────────────────────────────────────

def get_current_user():
    """
    Extract and verify the JWT token from Authorization header.
    Returns (user_id, None) on success, or (None, error_response) on failure.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Missing or invalid Authorization header"}), 401)

    token = auth_header.split(" ")[1]
    user_id = verify_token(token)

    if not user_id:
        return None, (jsonify({"error": "Invalid or expired token"}), 401)

    return user_id, None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/ping", methods=["GET"])
def ping():
    """Simple health check — no auth needed."""
    return jsonify({"status": "ok", "message": "Cloud Storage API is running ✅"})


@app.route("/api/health", methods=["GET"])
def health():
    """
    Check if both S3 buckets are available.
    Used by the frontend health dashboard.
    """
    user_id, err = get_current_user()
    if err:
        return err

    bucket_status = check_bucket_health()
    return jsonify({
        "status": "ok",
        "buckets": bucket_status
    })


@app.route("/api/upload", methods=["POST"])
def upload():
    """
    Upload a file:
    1. Receive file from frontend
    2. Encrypt with AES-256-GCM (Arfah's module)
    3. Split and upload to S3 across two regions (Anila's module)
    4. Save manifest to DynamoDB (Abdullah's database.py)
    """
    user_id, err = get_current_user()
    if err:
        return err

    # Check file was included
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file      = request.files["file"]
    file_name = file.filename
    file_bytes = file.read()
    file_size  = len(file_bytes)

    if file_size == 0:
        return jsonify({"error": "Empty file"}), 400

    if file_size > 100 * 1024 * 1024:  # 100 MB limit
        return jsonify({"error": "File too large (max 100 MB)"}), 400

    # Generate unique ID for this file
    file_id = str(uuid.uuid4())

    try:
        # Step 1: ENCRYPT (Arfah's module)
        print(f"[{file_id}] Encrypting '{file_name}' ({file_size} bytes)...")
        encryption_result = encrypt_file(file_bytes)
        encrypted_bytes   = encryption_result["ciphertext"]
        nonce             = encryption_result["nonce"]
        wrapped_dek       = encryption_result["wrapped_dek"]

        # Step 2: SHARD + UPLOAD (Anila's module)
        print(f"[{file_id}] Uploading shards to S3...")
        storage_result = upload_shards(file_id, encrypted_bytes)
        shard_manifest = storage_result["shard_manifest"]
        total_shards   = storage_result["total_shards"]

        # Step 3: SAVE TO DYNAMODB (Abdullah's module)
        print(f"[{file_id}] Saving metadata to DynamoDB...")
        saved = save_file_record(
            user_id       = user_id,
            file_id       = file_id,
            file_name     = file_name,
            file_size     = file_size,
            wrapped_dek   = wrapped_dek,
            nonce         = nonce,
            shard_manifest = shard_manifest,
            total_shards  = total_shards
        )

        if not saved:
            raise Exception("Failed to save file record to DynamoDB")

        print(f"[{file_id}] ✅ Upload complete!")
        return jsonify({
            "success":     True,
            "file_id":     file_id,
            "file_name":   file_name,
            "file_size":   file_size,
            "total_shards": total_shards,
            "message":     f"File uploaded and encrypted across {total_shards} shards in 2 AWS regions"
        }), 201

    except Exception as e:
        print(f"[{file_id}] ❌ Upload error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/files", methods=["GET"])
def list_files():
    """
    Get all files belonging to the current user.
    """
    user_id, err = get_current_user()
    if err:
        return err

    files = list_user_files(user_id)
    return jsonify({"files": files})


@app.route("/api/download/<file_id>", methods=["GET"])
def download(file_id):
    """
    Download and decrypt a file:
    1. Get the shard manifest from DynamoDB
    2. Download and reassemble shards from S3 (Anila's module)
    3. Decrypt the file (Arfah's module)
    4. Stream the original file back to the user
    """
    user_id, err = get_current_user()
    if err:
        return err

    # Step 1: Get file record from DynamoDB
    record = get_file_record(user_id, file_id)
    if not record:
        return jsonify({"error": "File not found"}), 404

    try:
        # Step 2: DOWNLOAD SHARDS (Anila's module)
        print(f"[{file_id}] Downloading shards from S3...")
        encrypted_bytes = download_shards(record["shardManifest"])

        # Step 3: DECRYPT (Arfah's module)
        print(f"[{file_id}] Decrypting file...")
        plaintext = decrypt_file(
            ciphertext    = encrypted_bytes,
            nonce_b64     = record["nonce"],
            wrapped_dek_b64 = record["wrapped_dek"]
        )

        print(f"[{file_id}] ✅ Download complete!")

        # Step 4: Send file to browser
        return send_file(
            io.BytesIO(plaintext),
            as_attachment      = True,
            download_name      = record["fileName"],
            mimetype           = "application/octet-stream"
        )

    except Exception as e:
        print(f"[{file_id}] ❌ Download error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/files/<file_id>", methods=["DELETE"])
def delete_file(file_id):
    """
    Delete a file:
    1. Get the shard manifest from DynamoDB
    2. Delete all shards from both S3 buckets
    3. Delete the DynamoDB record
    """
    user_id, err = get_current_user()
    if err:
        return err

    record = get_file_record(user_id, file_id)
    if not record:
        return jsonify({"error": "File not found"}), 404

    try:
        # Delete shards from S3
        delete_file_shards(file_id, record["shardManifest"])

        # Delete from DynamoDB
        delete_file_record(user_id, file_id)

        return jsonify({"success": True, "message": "File deleted from all regions"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    print("=" * 50)
    print(f"🚀 Cloud Storage API starting on port {port}")
    print(f"   Visit: http://localhost:{port}/api/ping")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=True)