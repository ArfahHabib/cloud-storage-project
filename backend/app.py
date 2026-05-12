"""
backend/app.py
==============
Anila Kiran — Backend API (Coordinator)
"""

import os
import sys
import uuid
import io
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

from security.encrypt      import encrypt_file, decrypt_file
from storage.shard_manager import upload_shards, download_shards, delete_file_shards, check_bucket_health
from backend.database      import save_file_record, get_file_record, list_user_files, delete_file_record
from backend.auth          import verify_token, get_user_id_from_token

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)


def get_current_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Missing or invalid Authorization header"}), 401)
    token   = auth_header.split(" ")[1]
    user_id = verify_token(token)
    if not user_id:
        return None, (jsonify({"error": "Invalid or expired token"}), 401)
    return user_id, None


@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "message": "Cloud Storage API is running ✅"})


@app.route("/api/health", methods=["GET"])
def health():
    user_id, err = get_current_user()
    if err:
        return err
    return jsonify({"status": "ok", "buckets": check_bucket_health()})


@app.route("/api/upload", methods=["POST"])
def upload():
    user_id, err = get_current_user()
    if err:
        return err

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file       = request.files["file"]
    file_name  = file.filename
    file_bytes = file.read()
    file_size  = len(file_bytes)

    if file_size == 0:
        return jsonify({"error": "Empty file"}), 400
    if file_size > 100 * 1024 * 1024:
        return jsonify({"error": "File too large (max 100 MB)"}), 400

    file_id = str(uuid.uuid4())

    try:
        print(f"[{file_id}] Encrypting '{file_name}' ({file_size} bytes)...")
        encryption_result = encrypt_file(file_bytes)
        encrypted_bytes   = encryption_result["ciphertext"]
        nonce             = encryption_result["nonce"]
        wrapped_dek       = encryption_result["wrapped_dek"]

        print(f"[{file_id}] Uploading shards to S3...")
        storage_result = upload_shards(file_id, encrypted_bytes)
        shard_manifest = storage_result["shard_manifest"]
        total_shards   = storage_result["total_shards"]

        print(f"[{file_id}] Saving metadata to DynamoDB...")
        saved = save_file_record(
            user_id        = user_id,
            file_id        = file_id,
            file_name      = file_name,
            file_size      = file_size,
            wrapped_dek    = wrapped_dek,
            nonce          = nonce,
            shard_manifest = shard_manifest,
            total_shards   = total_shards
        )
        if not saved:
            raise Exception("Failed to save file record to DynamoDB")

        print(f"[{file_id}] ✅ Upload complete!")
        return jsonify({
            "success":      True,
            "file_id":      file_id,
            "file_name":    file_name,
            "file_size":    file_size,
            "total_shards": total_shards,
            "message":      f"File uploaded and encrypted across {total_shards} shards in 2 AWS regions"
        }), 201

    except Exception as e:
        print(f"[{file_id}] ❌ Upload error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/files", methods=["GET"])
def list_files():
    user_id, err = get_current_user()
    if err:
        return err
    return jsonify({"files": list_user_files(user_id)})


@app.route("/api/download/<file_id>", methods=["GET"])
def download(file_id):
    user_id, err = get_current_user()
    if err:
        return err

    record = get_file_record(user_id, file_id)
    if not record:
        return jsonify({"error": "File not found"}), 404

    try:
        print(f"[{file_id}] Downloading shards from S3...")
        encrypted_bytes = download_shards(
            record["shardManifest"],
            total_shards=int(record["totalShards"])
        )

        print(f"[{file_id}] Decrypting file...")
        plaintext = decrypt_file(
            ciphertext      = encrypted_bytes,
            nonce_b64       = record["nonce"],
            wrapped_dek_b64 = record["wrapped_dek"]
        )

        print(f"[{file_id}] ✅ Download complete!")

        # Build response with Content-Length so browser can show progress
        response = send_file(
            io.BytesIO(plaintext),
            as_attachment = True,
            download_name = record["fileName"],
            mimetype      = "application/octet-stream"
        )
        response.headers["Content-Length"]             = len(plaintext)
        response.headers["Access-Control-Expose-Headers"] = "Content-Length"
        return response

    except Exception as e:
        print(f"[{file_id}] ❌ Download error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/files/<file_id>", methods=["DELETE"])
def delete_file(file_id):
    user_id, err = get_current_user()
    if err:
        return err

    record = get_file_record(user_id, file_id)
    if not record:
        return jsonify({"error": "File not found"}), 404

    try:
        delete_file_shards(file_id, record["shardManifest"])
        delete_file_record(user_id, file_id)
        return jsonify({"success": True, "message": "File deleted from all regions"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    print("=" * 50)
    print(f" Cloud Storage API starting on port {port}")
    print(f"   Visit: http://localhost:{port}/api/ping")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=True)
