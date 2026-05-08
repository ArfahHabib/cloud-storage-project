"""
storage/shard_manager.py
========================
ANILA KIRAN — Cloud Storage & S3 Integration

This module handles:
1. Splitting encrypted files into shards (pieces)
2. Uploading shards to TWO S3 buckets in parallel (different AWS regions)
3. Rolling back if one upload fails (atomic upload)
4. Downloading shards from both regions and reassembling them
5. Health check — reports if each S3 region is available

WHY TWO REGIONS?
- If us-east-1 goes down, eu-west-1 still has the shards
- An attacker who breaks into ONE bucket only gets half the file
- It mirrors real enterprise cloud storage architecture
"""

import os
import math
import uuid
import boto3
import threading
from typing import List, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()

# ── AWS Config ────────────────────────────────────────────────────────────────
BUCKET_PRIMARY   = os.getenv("S3_BUCKET_PRIMARY",   "cloudproject-shards-us")
BUCKET_SECONDARY = os.getenv("S3_BUCKET_SECONDARY", "cloudproject-shards-eu")
REGION_PRIMARY   = os.getenv("AWS_REGION_PRIMARY",   "us-east-1")
REGION_SECONDARY = os.getenv("AWS_REGION_SECONDARY", "eu-west-1")

# Create S3 clients for BOTH regions
s3_primary   = boto3.client("s3", region_name=REGION_PRIMARY)
s3_secondary = boto3.client("s3", region_name=REGION_SECONDARY)

# Number of shards to split file into
NUM_SHARDS = 4  # 4 total: 2 go to primary bucket, 2 go to secondary bucket


# ── Sharding Logic ────────────────────────────────────────────────────────────

def split_into_shards(data: bytes, num_shards: int = NUM_SHARDS) -> List[bytes]:
    """
    Split bytes into equal-sized shards.
    The last shard may be slightly larger if the file doesn't divide evenly.
    
    Example: 1000 bytes split into 4 shards → [250, 250, 250, 250] bytes
    """
    shard_size = math.ceil(len(data) / num_shards)
    shards = []
    for i in range(num_shards):
        start = i * shard_size
        end   = start + shard_size
        shard = data[start:end]
        if shard:  # Don't add empty shards
            shards.append(shard)
    return shards


def reassemble_shards(shards: List[bytes]) -> bytes:
    """
    Reassemble shards back into the original file bytes.
    Shards must be in the correct order (sorted by shard index).
    """
    return b"".join(shards)


# ── Upload Logic ──────────────────────────────────────────────────────────────

def _upload_single_shard(s3_client, bucket: str, key: str, data: bytes,
                          results: dict, result_key: str):
    """
    Upload one shard to one S3 bucket.
    Stores success/failure in the shared results dict.
    This runs in a background thread for parallel uploads.
    """
    try:
        s3_client.put_object(
            Bucket      = bucket,
            Key         = key,
            Body        = data,
            ContentType = "application/octet-stream"
        )
        results[result_key] = {"success": True}
    except Exception as e:
        results[result_key] = {"success": False, "error": str(e)}


def upload_shards(file_id: str, encrypted_bytes: bytes) -> Dict:
    """
    Split an encrypted file into shards and upload to BOTH S3 buckets in parallel.

    Distribution strategy:
    - Even-indexed shards (0, 2) → PRIMARY bucket (us-east-1)
    - Odd-indexed shards  (1, 3) → SECONDARY bucket (eu-west-1)

    Returns a shard manifest dict that gets stored in DynamoDB.
    Raises an exception and ROLLS BACK if any upload fails.
    """
    shards = split_into_shards(encrypted_bytes)
    print(f"Split file into {len(shards)} shards")

    threads = []
    results = {}
    shard_manifest = []  # Will store location of each shard

    # Start all uploads simultaneously using threads
    for idx, shard_data in enumerate(shards):
        if idx % 2 == 0:
            # Even index → PRIMARY bucket
            bucket    = BUCKET_PRIMARY
            s3_client = s3_primary
            region    = REGION_PRIMARY
        else:
            # Odd index → SECONDARY bucket
            bucket    = BUCKET_SECONDARY
            s3_client = s3_secondary
            region    = REGION_SECONDARY

        shard_key    = f"{file_id}/shard_{idx:04d}"  # e.g., "abc123/shard_0000"
        result_key   = f"shard_{idx}"

        shard_manifest.append({
            "shard_index": idx,
            "bucket":      bucket,
            "region":      region,
            "s3_key":      shard_key,
            "size_bytes":  len(shard_data)
        })

        t = threading.Thread(
            target=_upload_single_shard,
            args=(s3_client, bucket, shard_key, shard_data, results, result_key)
        )
        threads.append(t)
        t.start()

    # Wait for ALL uploads to finish
    for t in threads:
        t.join()

    # Check if any failed
    failed = [k for k, v in results.items() if not v["success"]]
    if failed:
        print(f"Upload failed for: {failed}. Rolling back...")
        _rollback_uploads(file_id, shard_manifest, results)
        raise Exception(f"Upload failed for shards: {failed}. All uploads rolled back.")

    print(f"✅ All {len(shards)} shards uploaded successfully!")
    return {
        "file_id":        file_id,
        "total_shards":   len(shards),
        "shard_manifest": shard_manifest
    }


def _rollback_uploads(file_id: str, shard_manifest: list, results: dict):
    """
    If any shard upload fails, delete all successfully uploaded shards.
    This prevents orphaned partial files in S3.
    """
    for shard_info in shard_manifest:
        idx        = shard_info["shard_index"]
        result_key = f"shard_{idx}"
        if results.get(result_key, {}).get("success"):
            try:
                if shard_info["region"] == REGION_PRIMARY:
                    s3_primary.delete_object(
                        Bucket=shard_info["bucket"],
                        Key=shard_info["s3_key"]
                    )
                else:
                    s3_secondary.delete_object(
                        Bucket=shard_info["bucket"],
                        Key=shard_info["s3_key"]
                    )
                print(f"  Rolled back shard {idx}")
            except Exception as e:
                print(f"  Warning: Could not roll back shard {idx}: {e}")


# ── Download Logic ────────────────────────────────────────────────────────────

def download_shards(shard_manifest: list) -> bytes:
    """
    Download all shards from S3 and reassemble them.
    
    Args:
    - shard_manifest: list of dicts from DynamoDB (tells us where each shard is)
    
    Returns the full encrypted file bytes.
    """
    threads     = []
    shard_data  = {}  # {shard_index: bytes}

    def _download_one(shard_info: dict):
        idx    = shard_info["shard_index"]
        bucket = shard_info["bucket"]
        key    = shard_info["s3_key"]
        region = shard_info["region"]

        s3_client = s3_primary if region == REGION_PRIMARY else s3_secondary
        try:
            response        = s3_client.get_object(Bucket=bucket, Key=key)
            shard_data[idx] = response["Body"].read()
        except Exception as e:
            raise Exception(f"Failed to download shard {idx} from {bucket}: {e}")

    # Download all shards in parallel
    for shard_info in shard_manifest:
        t = threading.Thread(target=_download_one, args=(shard_info,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Sort shards by index and reassemble
    sorted_shards = [shard_data[i] for i in sorted(shard_data.keys())]
    return reassemble_shards(sorted_shards)


def delete_file_shards(file_id: str, shard_manifest: list):
    """
    Permanently delete all shards of a file from both S3 buckets.
    Called when a user deletes a file.
    """
    for shard_info in shard_manifest:
        region = shard_info["region"]
        s3_client = s3_primary if region == REGION_PRIMARY else s3_secondary
        try:
            s3_client.delete_object(
                Bucket=shard_info["bucket"],
                Key=shard_info["s3_key"]
            )
        except Exception as e:
            print(f"Warning: Could not delete shard {shard_info['s3_key']}: {e}")


# ── Health Check ──────────────────────────────────────────────────────────────

def check_bucket_health() -> Dict:
    """
    Check if both S3 buckets are accessible and responding.
    Returns health status for the frontend dashboard.
    """
    status = {}

    # Check primary bucket
    try:
        s3_primary.head_bucket(Bucket=BUCKET_PRIMARY)
        status["primary"] = {
            "bucket": BUCKET_PRIMARY,
            "region": REGION_PRIMARY,
            "status": "healthy",
            "available": True
        }
    except Exception as e:
        status["primary"] = {
            "bucket": BUCKET_PRIMARY,
            "region": REGION_PRIMARY,
            "status": f"error: {str(e)}",
            "available": False
        }

    # Check secondary bucket
    try:
        s3_secondary.head_bucket(Bucket=BUCKET_SECONDARY)
        status["secondary"] = {
            "bucket": BUCKET_SECONDARY,
            "region": REGION_SECONDARY,
            "status": "healthy",
            "available": True
        }
    except Exception as e:
        status["secondary"] = {
            "bucket": BUCKET_SECONDARY,
            "region": REGION_SECONDARY,
            "status": f"error: {str(e)}",
            "available": False
        }

    return status


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Testing storage module...")
    print("=" * 50)

    # Test sharding logic (no AWS needed)
    test_data  = b"ABCDEFGHIJ" * 100  # 1000 bytes
    shards     = split_into_shards(test_data, 4)
    reassembled = reassemble_shards(shards)

    print(f"\nOriginal size:    {len(test_data)} bytes")
    print(f"Number of shards: {len(shards)}")
    for i, s in enumerate(shards):
        print(f"  Shard {i}: {len(s)} bytes")
    print(f"Reassembled size: {len(reassembled)} bytes")

    assert reassembled == test_data
    print("\n✅ Shard split/reassemble works correctly!")

    # Test S3 health (requires AWS credentials)
    print("\nChecking S3 bucket health...")
    health = check_bucket_health()
    for name, info in health.items():
        icon = "✅" if info["available"] else "❌"
        print(f"  {icon} {name}: {info['bucket']} ({info['region']}) — {info['status']}")