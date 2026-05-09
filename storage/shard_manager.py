"""
storage/shard_manager.py
========================
RAID-5-style sharding across two S3 buckets.

For every pair of data shards (shard_0, shard_1), a XOR parity shard
is computed and stored in both buckets. If either data shard is lost,
it can be reconstructed from the other + parity.

Layout (example, 4 data shards):
  Primary bucket:   data_0000, data_0002, parity_0000, parity_0002(mirror)
  Secondary bucket: data_0001, data_0003, parity_0000(mirror), parity_0002

Recovery:
  - data_0000 missing → parity_0000 XOR data_0001
  - data_0001 missing → parity_0000 XOR data_0000
  - Both missing      → unrecoverable (RAID-5 limit)
"""

import os
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

PRIMARY_BUCKET   = os.getenv("S3_BUCKET_PRIMARY",   "cloud-storage-primary")
SECONDARY_BUCKET = os.getenv("S3_BUCKET_SECONDARY", "cloud-storage-secondary")
PRIMARY_REGION   = os.getenv("AWS_REGION_PRIMARY",  "us-east-1")
SECONDARY_REGION = os.getenv("AWS_REGION_SECONDARY","us-west-2")
SHARD_SIZE       = int(os.getenv("SHARD_SIZE_BYTES", 5 * 1024 * 1024))

s3_primary   = boto3.client("s3", region_name=PRIMARY_REGION)
s3_secondary = boto3.client("s3", region_name=SECONDARY_REGION)

_BUCKETS = [
    (PRIMARY_BUCKET,   s3_primary),
    (SECONDARY_BUCKET, s3_secondary),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _s3_for(bucket):
    return s3_primary if bucket == PRIMARY_BUCKET else s3_secondary

def _xor_chunks(chunks: list) -> bytes:
    """XOR a list of byte strings together. Pads shorter chunks with 0x00."""
    max_len = max(len(c) for c in chunks)
    result  = bytearray(max_len)
    for chunk in chunks:
        for i, b in enumerate(chunk):
            result[i] ^= b
    return bytes(result)

def _put(bucket, s3, key, data):
    s3.put_object(Bucket=bucket, Key=key, Body=data)
    return {"bucket": bucket, "key": key}

def _get(bucket, s3, key) -> bytes:
    return s3.get_object(Bucket=bucket, Key=key)["Body"].read()

def _delete_key(bucket, s3, key):
    try:
        s3.delete_object(Bucket=bucket, Key=key)
    except ClientError as e:
        print(f"Warning: could not delete {key} from {bucket}: {e}")


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_shards(file_id: str, encrypted_bytes: bytes) -> dict:
    """
    Split into SHARD_SIZE chunks, compute XOR parity per pair, upload all
    in parallel. Returns shard_manifest and total_shards (data shards only).
    """
    total_data = math.ceil(len(encrypted_bytes) / SHARD_SIZE) or 1
    chunks = [
        encrypted_bytes[i * SHARD_SIZE : (i + 1) * SHARD_SIZE]
        for i in range(total_data)
    ]

    # Pad to even number so every shard has a pair
    padded = False
    if len(chunks) % 2 != 0:
        chunks.append(bytes(len(chunks[-1])))  # zero-pad same size as last chunk
        padded = True

    tasks    = []  # (bucket, s3, key, data)
    manifest = []

    # Data shards — alternate between primary and secondary
    for i, chunk in enumerate(chunks):
        bucket, s3 = _BUCKETS[i % 2]
        key        = f"shards/{file_id}/data_{i:04d}"
        tasks.append((bucket, s3, key, chunk))
        manifest.append({
            "bucket": bucket, "key": key,
            "index": i, "type": "data"
        })

    # Parity shards — one per pair, mirrored to both buckets
    for pair_i in range(0, len(chunks), 2):
        parity = _xor_chunks([chunks[pair_i], chunks[pair_i + 1]])
        p_key  = f"shards/{file_id}/parity_{pair_i:04d}"

        # Primary copy
        tasks.append((PRIMARY_BUCKET, s3_primary, p_key, parity))
        manifest.append({
            "bucket": PRIMARY_BUCKET, "key": p_key,
            "pair": pair_i, "type": "parity"
        })
        # Mirror copy
        tasks.append((SECONDARY_BUCKET, s3_secondary, p_key, parity))
        manifest.append({
            "bucket": SECONDARY_BUCKET, "key": p_key,
            "pair": pair_i, "type": "parity_mirror"
        })

    # Upload everything in parallel; roll back on any failure
    uploaded = []
    try:
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(_put, b, s, k, d): (b, s, k)
                       for b, s, k, d in tasks}
            for fut in as_completed(futures):
                b, s, k = futures[fut]
                fut.result()  # raises on S3 error
                uploaded.append((b, s, k))
    except Exception:
        # Roll back every shard that succeeded before the failure
        for b, s, k in uploaded:
            _delete_key(b, s, k)
        raise

    return {
        "shard_manifest": manifest,
        "total_shards":   total_data,  # real data shards only (excludes pad)
    }


# ── Download ──────────────────────────────────────────────────────────────────

def download_shards(shard_manifest: list, total_shards: int = None) -> bytes:
    """
    Download data shards in parallel. If a data shard is missing/unreachable,
    reconstruct it from its pair-mate + XOR parity. Falls back to parity
    mirror if the primary parity copy is also unavailable.

    total_shards: the original count of real data shards (from DynamoDB).
                  Used to strip any zero-pad shard added during upload.
    """
    data_entries = sorted(
        [e for e in shard_manifest if e["type"] == "data"],
        key=lambda e: e["index"]
    )
    # Build parity lookup: pair_start → (primary_entry, mirror_entry)
    parity_primary = {
        e["pair"]: e for e in shard_manifest if e["type"] == "parity"
    }
    parity_mirror = {
        e["pair"]: e for e in shard_manifest if e["type"] == "parity_mirror"
    }

    # Download all data shards in parallel
    results  = {}  # index → bytes
    failures = {}  # index → entry

    def _fetch_data(entry):
        return entry["index"], _get(entry["bucket"], _s3_for(entry["bucket"]), entry["key"])

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_fetch_data, e): e for e in data_entries}
        for fut in as_completed(futures):
            entry = futures[fut]
            try:
                idx, data = fut.result()
                results[idx] = data
            except ClientError:
                print(f"[RAID] data shard {entry['index']} unavailable, will attempt recovery")
                failures[entry["index"]] = entry

    # Recover failed shards via XOR parity
    for failed_idx in failures:
        pair_start = (failed_idx // 2) * 2
        pair_other = pair_start + 1 if failed_idx == pair_start else pair_start

        if pair_other not in results:
            raise Exception(
                f"Unrecoverable: both shard_{failed_idx} and shard_{pair_other} "
                f"are unavailable — RAID-5 cannot recover from 2 simultaneous losses."
            )

        # Fetch parity — try primary copy first, fall back to mirror
        parity = None
        for p_entry in [parity_primary.get(pair_start), parity_mirror.get(pair_start)]:
            if p_entry is None:
                continue
            try:
                parity = _get(p_entry["bucket"], _s3_for(p_entry["bucket"]), p_entry["key"])
                break
            except ClientError:
                print(f"[RAID] parity copy in {p_entry['bucket']} unavailable, trying mirror...")

        if parity is None:
            raise Exception(
                f"Both parity copies for pair {pair_start} are unavailable — cannot recover shard_{failed_idx}."
            )

        print(f"[RAID] Reconstructing shard_{failed_idx} from parity + shard_{pair_other}")
        results[failed_idx] = _xor_chunks([results[pair_other], parity])

    # Reassemble in order
    ordered = [results[e["index"]] for e in data_entries]

    # Strip zero-pad shard if upload added one
    if total_shards is not None and len(ordered) > total_shards:
        ordered = ordered[:total_shards]

    return b"".join(ordered)


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_file_shards(file_id: str, shard_manifest: list) -> None:
    """Delete all data and parity shards in parallel. Logs but ignores errors."""
    with ThreadPoolExecutor(max_workers=8) as ex:
        for entry in shard_manifest:
            ex.submit(_delete_key, entry["bucket"], _s3_for(entry["bucket"]), entry["key"])


# ── Health ────────────────────────────────────────────────────────────────────

def check_bucket_health() -> dict:
    def _reachable(s3_client, bucket):
        try:
            s3_client.head_bucket(Bucket=bucket)
            return True
        except ClientError:
            return False

    return {
        "primary":   _reachable(s3_primary,   PRIMARY_BUCKET),
        "secondary": _reachable(s3_secondary, SECONDARY_BUCKET),
    }