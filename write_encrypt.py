content = """\
import os, base64, boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv
load_dotenv()

KMS_KEY_ID = os.getenv("KMS_KEY_ID", "")
AWS_REGION = os.getenv("AWS_REGION_PRIMARY", "us-east-1")
kms = boto3.client("kms", region_name=AWS_REGION)

def _b64enc(b): return base64.b64encode(b).decode("utf-8")
def _b64dec(s): return base64.b64decode(s)

def encrypt_file(plaintext: bytes) -> dict:
    if not KMS_KEY_ID:
        raise EnvironmentError("KMS_KEY_ID is not set in .env")
    resp = kms.generate_data_key(KeyId=KMS_KEY_ID, KeySpec="AES_256")
    dek = resp["Plaintext"]
    wrapped_dek = _b64enc(resp["CiphertextBlob"])
    nonce = os.urandom(12)
    ciphertext = AESGCM(dek).encrypt(nonce, plaintext, None)
    return {"ciphertext": ciphertext, "nonce": _b64enc(nonce), "wrapped_dek": wrapped_dek}

def decrypt_file(ciphertext: bytes, nonce_b64: str, wrapped_dek_b64: str) -> bytes:
    if not KMS_KEY_ID:
        raise EnvironmentError("KMS_KEY_ID is not set in .env")
    dek = kms.decrypt(CiphertextBlob=_b64dec(wrapped_dek_b64))["Plaintext"]
    return AESGCM(dek).decrypt(_b64dec(nonce_b64), ciphertext, None)
"""

with open("security/encrypt.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Written OK")
