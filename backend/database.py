"""
backend/database.py
===================
Anila kiran — Database Layer

This module handles all DynamoDB operations:
- Saving file metadata and shard manifests after upload
- Retrieving file records for download
- Listing all files for a user
- Deleting file records

DynamoDB Table Schema:
  Partition Key: userId  (string) — the Cognito user's ID
  Sort Key:      fileId  (string) — unique UUID per file

Each item contains:
  - userId
  - fileId
  - fileName (original filename)
  - fileSize (bytes)
  - uploadedAt (ISO timestamp)
  - wrapped_dek (KMS-encrypted encryption key)
  - nonce (AES-GCM nonce, base64)
  - shard_manifest (list of shard locations)
  - total_shards
"""

import os
import boto3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "FileManifest")
AWS_REGION     = os.getenv("AWS_REGION_PRIMARY", "us-east-1")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table    = dynamodb.Table(DYNAMODB_TABLE)


def save_file_record(user_id: str, file_id: str, file_name: str,
                     file_size: int, wrapped_dek: str, nonce: str,
                     shard_manifest: list, total_shards: int) -> bool:
    """
    Save a new file record to DynamoDB after a successful upload.
    Returns True if successful.
    """
    try:
        table.put_item(Item={
            "userId":        user_id,
            "fileId":        file_id,
            "fileName":      file_name,
            "fileSize":      file_size,
            "uploadedAt":    datetime.utcnow().isoformat() + "Z",
            "wrapped_dek":   wrapped_dek,
            "nonce":         nonce,
            "shardManifest": shard_manifest,
            "totalShards":   total_shards
        })
        return True
    except Exception as e:
        print(f"DynamoDB save error: {e}")
        return False


def get_file_record(user_id: str, file_id: str) -> dict | None:
    """
    Retrieve a single file record by userId + fileId.
    Returns the record dict, or None if not found.
    """
    try:
        response = table.get_item(Key={
            "userId": user_id,
            "fileId": file_id
        })
        return response.get("Item")
    except Exception as e:
        print(f"DynamoDB get error: {e}")
        return None


def list_user_files(user_id: str) -> list:
    """
    Get all files belonging to a user.
    Returns a list of file records (without the sensitive shard manifest details).
    """
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("userId").eq(user_id),
            ProjectionExpression="fileId, fileName, fileSize, uploadedAt, totalShards"
        )
        return response.get("Items", [])
    except Exception as e:
        print(f"DynamoDB list error: {e}")
        return []


def delete_file_record(user_id: str, file_id: str) -> bool:
    """
    Delete a file record from DynamoDB.
    Call this AFTER deleting the S3 shards.
    Returns True if successful.
    """
    try:
        table.delete_item(Key={
            "userId": user_id,
            "fileId": file_id
        })
        return True
    except Exception as e:
        print(f"DynamoDB delete error: {e}")
        return False
