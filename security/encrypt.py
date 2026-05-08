"""
security/encrypt.py
===================
ARFAH HABIB — Security & Key Management

This module handles:
1. Generating a unique Data Encryption Key (DEK) per file
2. Encrypting files with AES-256-GCM (military-grade encryption)
3. Wrapping the DEK with AWS KMS (Envelope Encryption)
4. Decrypting files on download

HOW ENVELOPE ENCRYPTION WORKS:
- AWS KMS stores your Master Key (CMK) — it never leaves AWS
- We generate a random DEK (Data Encryption Key) for each file
- We encrypt the file with the DEK
- We ask KMS to encrypt (wrap) the DEK itself
- We store the wrapped DEK in DynamoDB (safe — it's encrypted)
- To decrypt: ask KMS to unwrap the DEK, then use it to decrypt the file
"""

import os
import boto3
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv

load_dotenv()

# ── AWS Config ──────────────────────────────────────────────────────────────
KMS_KEY_ID   = os.getenv("KMS_KEY_ID")
AWS_REGION   = os.getenv("AWS_REGION_PRIMARY", "us-east-1")

kms_client = boto3.client("kms", region_name=AWS_REGION)


# ── Key Generation ───────────────────────────────────────────────────────────

def generate_dek() -> bytes:
    """
    Generate a random 256-bit (32 byte) Data Encryption Key.
    This key is unique per file — never reused.
    """
    return os.urandom(32)  # 32 bytes = 256 bits = AES-256


def wrap_dek_with_kms(dek: bytes) -> str:
    """
    Send the DEK to AWS KMS to encrypt it using our Customer Master Key.
    Returns a base64-encoded string of the encrypted DEK.
    This is safe to store in DynamoDB.
    """
    response = kms_client.encrypt(
        KeyId     = KMS_KEY_ID,
        Plaintext = dek
    )
    encrypted_dek = response["CiphertextBlob"]
    return base64.b64encode(encrypted_dek).decode("utf-8")


def unwrap_dek_from_kms(wrapped_dek_b64: str) -> bytes:
    """
    Ask AWS KMS to decrypt the wrapped DEK back into the original key bytes.
    Only works if you have the correct IAM permissions.
    """
    encrypted_dek = base64.b64decode(wrapped_dek_b64)
    response = kms_client.decrypt(
        CiphertextBlob = encrypted_dek
    )
    return response["Plaintext"]


# ── File Encryption ──────────────────────────────────────────────────────────

def encrypt_file(file_bytes: bytes) -> dict:
    """
    Encrypt a file using AES-256-GCM.

    Returns a dict with:
    - 'ciphertext': the encrypted file bytes
    - 'nonce':      the 12-byte random nonce (needed for decryption)
    - 'wrapped_dek': the KMS-encrypted DEK (safe to store in DB)

    AES-GCM provides both encryption AND authentication (it detects tampering).
    """
    # Step 1: Generate a fresh DEK for this file
    dek = generate_dek()

    # Step 2: Generate a random 96-bit nonce (required by AES-GCM)
    # Never reuse a nonce with the same key!
    nonce = os.urandom(12)  # 12 bytes = 96 bits

    # Step 3: Encrypt the file
    aesgcm     = AESGCM(dek)
    ciphertext = aesgcm.encrypt(nonce, file_bytes, None)

    # Step 4: Wrap the DEK with KMS so we can store it safely
    wrapped_dek = wrap_dek_with_kms(dek)

    # Clear the plaintext DEK from memory
    del dek

    return {
        "ciphertext":  ciphertext,
        "nonce":       base64.b64encode(nonce).decode("utf-8"),
        "wrapped_dek": wrapped_dek
    }


def decrypt_file(ciphertext: bytes, nonce_b64: str, wrapped_dek_b64: str) -> bytes:
    """
    Decrypt a file.

    Args:
    - ciphertext:     The encrypted file bytes
    - nonce_b64:      Base64-encoded nonce from the upload record
    - wrapped_dek_b64: Base64-encoded KMS-wrapped DEK from DynamoDB

    Returns the original plaintext file bytes.
    """
    # Step 1: Ask KMS to unwrap the DEK
    dek   = unwrap_dek_from_kms(wrapped_dek_b64)
    nonce = base64.b64decode(nonce_b64)

    # Step 2: Decrypt the file
    aesgcm    = AESGCM(dek)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    del dek
    return plaintext


# ── Test (run this file directly to test) ────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Testing encryption module...")
    print("=" * 50)

    # Create a fake file for testing
    test_data = b"Hello, this is a secret file! " * 100
    print(f"Original file size: {len(test_data)} bytes")

    # Encrypt
    print("\nEncrypting...")
    result = encrypt_file(test_data)
    print(f"Encrypted size:  {len(result['ciphertext'])} bytes")
    print(f"Nonce:           {result['nonce'][:20]}...")
    print(f"Wrapped DEK:     {result['wrapped_dek'][:40]}...")

    # Decrypt
    print("\nDecrypting...")
    recovered = decrypt_file(
        result["ciphertext"],
        result["nonce"],
        result["wrapped_dek"]
    )
    print(f"Decrypted size:  {len(recovered)} bytes")

    # Verify
    assert recovered == test_data, "ERROR: Decrypted data does not match original!"
    print("\n✅ SUCCESS: Encryption and decryption work correctly!")