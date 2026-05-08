"""
storage/shard_manager.py
========================
ANILA — S3 Shard Manager

Splits encrypted file bytes into 4 equal chunks and distributes them
across two S3 buckets in two AWS regions for geographic redundancy.

Shard distribution (N=4):
  Shards 0, 1  →  S3_BUCKET_PRIMARY   (eu-west-1)
  Shards 2, 3  →  S3_BUCKET_SECONDARY (us-east-1)

All uploads, downloads, and deletes run in parallel across all 4 shards,
so total time ≈ slowest single shard (not sum of all shards).

Environment variables required (.env):
  S3_BUCKET_PRIMARY      — e.g. cloudproject-shards-us
  S3_BUCKET_SECONDARY    — e.g. cloudproject-shards-eu
  AWS_REGION_PRIMARY     — e.g. eu-west-1
  AWS_REGION_SECONDARY   — e.g. us-east-1
  AWS_ACCESS_KEY_ID      — your AWS access key
  AWS_SECRET_ACCESS_KEY  — your AWS secret key
"""

import os
import math
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

BUCKET_PRIMARY        = os.getenv("S3_BUCKET_PRIMARY")
BUCKET_SECONDARY      = os.getenv("S3_BUCKET_SECONDARY")
REGION_PRIMARY        = os.getenv("AWS_REGION_PRIMARY",   "eu-west-1")
REGION_SECONDARY      = os.getenv("AWS_REGION_SECONDARY", "us-east-1")
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

NUM_SHARDS = 4  # fixed: 2 shards per bucket

# Shard index → (bucket, region)
SHARD_ROUTING = {
    0: (BUCKET_PRIMARY,   REGION_PRIMARY),
    1: (BUCKET_PRIMARY,   REGION_PRIMARY),
    2: (BUCKET_SECONDARY, REGION_SECONDARY),
    3: (BUCKET_SECONDARY, REGION_SECONDARY),
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _s3_client(region: str):
    """Create a boto3 S3 client for the given region."""
    return boto3.client(
        "s3",
        region_name           = region,
        aws_access_key_id     = AWS_ACCESS_KEY_ID,
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
    )


def _split_into_shards(data: bytes, n: int) -> list:
    """Split bytes into n roughly equal chunks."""
    shard_size = math.ceil(len(data) / n)
    return [data[i * shard_size:(i + 1) * shard_size] for i in range(n)]


def _s3_key(file_id: str, shard_index: int) -> str:
    """S3 object key for a shard."""
    return f"shards/{file_id}/shard_{shard_index}"


# ── Public API ─────────────────────────────────────────────────────────────────

def upload_shards(file_id: str, encrypted_bytes: bytes) -> dict:
    """
    Split encrypted_bytes into 4 shards and upload to S3 in parallel.

    All 4 shards are uploaded simultaneously across both regions,
    so total time ≈ slowest single shard instead of sum of all shards.

    Returns:
        {
            "shard_manifest": [ { shard_id, index, bucket, region, s3_key, size }, ... ],
            "total_shards":   4
        }

    Raises:
        Exception if any shard upload fails.
    """
    chunks = _split_into_shards(encrypted_bytes, NUM_SHARDS)

    def _upload_one(index, chunk):
        bucket, region = SHARD_ROUTING[index]
        s3_key         = _s3_key(file_id, index)
        client         = _s3_client(region)

        print(f"  [shard {index}] Uploading {len(chunk)} bytes → s3://{bucket}/{s3_key}")

        client.put_object(
            Bucket      = bucket,
            Key         = s3_key,
            Body        = chunk,
            ContentType = "application/octet-stream",
        )

        return {
            "shard_id": f"{file_id}_shard_{index}",
            "index":    index,
            "bucket":   bucket,
            "region":   region,
            "s3_key":   s3_key,
            "size":     len(chunk),
        }

    results = {}
    with ThreadPoolExecutor(max_workers=NUM_SHARDS) as executor:
        futures = {
            executor.submit(_upload_one, index, chunk): index
            for index, chunk in enumerate(chunks)
        }
        for future in as_completed(futures):
            shard_info = future.result()  # raises immediately if any upload failed
            results[shard_info["index"]] = shard_info

    # Return manifest sorted by index for consistency
    shard_manifest = [results[i] for i in range(NUM_SHARDS)]

    return {
        "shard_manifest": shard_manifest,
        "total_shards":   NUM_SHARDS,
    }


def download_shards(shard_manifest: list) -> bytes:
    """
    Download all shards from S3 in parallel and reassemble in order.

    Args:
        shard_manifest: list of shard dicts from upload_shards()

    Returns:
        Reassembled encrypted bytes.

    Raises:
        Exception if any shard download fails.
    """
    def _download_one(shard):
        client = _s3_client(shard["region"])

        print(f"  [shard {shard['index']}] Downloading s3://{shard['bucket']}/{shard['s3_key']}")

        response = client.get_object(
            Bucket = shard["bucket"],
            Key    = shard["s3_key"],
        )
        return shard["index"], response["Body"].read()

    results = {}
    with ThreadPoolExecutor(max_workers=NUM_SHARDS) as executor:
        futures = {executor.submit(_download_one, shard): shard["index"] for shard in shard_manifest}
        for future in as_completed(futures):
            index, chunk = future.result()  # raises immediately if any download failed
            results[index] = chunk

    # Reassemble in correct order
    return b"".join(results[i] for i in range(NUM_SHARDS))


def delete_file_shards(file_id: str, shard_manifest: list) -> bool:
    """
    Delete all shards from both S3 buckets in parallel.

    Args:
        file_id:        the file's UUID (used for logging)
        shard_manifest: list of shard dicts from upload_shards()

    Returns:
        True if all deletions succeeded.

    Raises:
        Exception if any shard deletion fails.
    """
    def _delete_one(shard):
        client = _s3_client(shard["region"])

        print(f"  [shard {shard['index']}] Deleting s3://{shard['bucket']}/{shard['s3_key']}")

        client.delete_object(
            Bucket = shard["bucket"],
            Key    = shard["s3_key"],
        )

    with ThreadPoolExecutor(max_workers=NUM_SHARDS) as executor:
        futures = [executor.submit(_delete_one, shard) for shard in shard_manifest]
        for future in as_completed(futures):
            future.result()  # raises immediately if any deletion failed

    return True


def check_bucket_health() -> dict:
    """
    Ping both S3 buckets in parallel with a lightweight head_bucket call.

    Returns:
        {
            "<region>": "healthy" | "unreachable: <reason>",
            ...
        }
    """
    def _check_one(bucket, region):
        try:
            _s3_client(region).head_bucket(Bucket=bucket)
            return region, "healthy"
        except Exception as e:
            return region, f"unreachable: {str(e)}"

    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_check_one, BUCKET_PRIMARY,   REGION_PRIMARY),
            executor.submit(_check_one, BUCKET_SECONDARY, REGION_SECONDARY),
        ]
        for future in as_completed(futures):
            region, status = future.result()
            results[region] = status

    return results