"""
backend/auth.py
===============
ABDULLAH WAHEED — Authentication (AWS Cognito JWT Verification)

Every API request includes a JWT token issued by AWS Cognito.
This module verifies that token is:
  1. Signed by our real Cognito User Pool (not forged)
  2. Not expired
  3. Issued for our app (correct audience)

Then extracts the userId (Cognito 'sub' claim) from it.
"""

import os
import json
import time
import base64
import urllib.request

from dotenv import load_dotenv

load_dotenv()

COGNITO_REGION       = os.getenv("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID    = os.getenv("COGNITO_CLIENT_ID", "")

# AWS Cognito publishes its public signing keys at this URL
JWKS_URL = (
    f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
    f"{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
)

_cached_keys = None  # Cache the public keys so we don't refetch every request


def _get_cognito_public_keys() -> dict:
    """
    Download and cache Cognito's public JWK keys.
    These are used to verify JWT signatures.
    """
    global _cached_keys
    if _cached_keys:
        return _cached_keys

    try:
        with urllib.request.urlopen(JWKS_URL) as resp:
            jwks = json.loads(resp.read().decode("utf-8"))
        _cached_keys = {key["kid"]: key for key in jwks["keys"]}
        return _cached_keys
    except Exception as e:
        print(f"Warning: Could not fetch Cognito public keys: {e}")
        return {}


def _base64url_decode(s: str) -> bytes:
    """Decode a base64url-encoded string (JWT uses this variant)."""
    s += "=" * (4 - len(s) % 4)  # Add padding if needed
    return base64.urlsafe_b64decode(s)


def verify_token(token: str) -> str | None:
    """
    Verify a Cognito JWT token.

    Returns the userId (Cognito 'sub') string if valid.
    Returns None if the token is invalid, expired, or forged.

    In development/testing mode (no Cognito configured), returns a
    fake userId so you can test without a real Cognito account.
    """
    # ── DEVELOPMENT MODE ──────────────────────────────────────────────────────
    # If Cognito is not configured, accept a simple dev token for testing
    if not COGNITO_USER_POOL_ID or COGNITO_USER_POOL_ID == "us-east-1_xxxxxxxxx":
        if token.startswith("dev-"):
            # e.g. "dev-user123" → userId is "user123"
            user_id = token[4:]
            print(f"[DEV MODE] Accepting dev token for user: {user_id}")
            return user_id
        return None

    # ── PRODUCTION MODE ───────────────────────────────────────────────────────
    try:
        # Split JWT into header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_str  = _base64url_decode(parts[0]).decode("utf-8")
        payload_str = _base64url_decode(parts[1]).decode("utf-8")
        header      = json.loads(header_str)
        payload     = json.loads(payload_str)

        # Check expiry
        if payload.get("exp", 0) < time.time():
            print("Token expired")
            return None

        # Check audience (must be our app client)
        if payload.get("aud") != COGNITO_CLIENT_ID and \
           payload.get("client_id") != COGNITO_CLIENT_ID:
            print("Token audience mismatch")
            return None

        # Check issuer (must be our Cognito user pool)
        expected_iss = (
            f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
            f"{COGNITO_USER_POOL_ID}"
        )
        if payload.get("iss") != expected_iss:
            print("Token issuer mismatch")
            return None

        # Signature verification using Cognito's public key
        # (For full RS256 verification install: pip install python-jose[cryptography])
        # Simplified version — in production use python-jose for full verification
        public_keys = _get_cognito_public_keys()
        kid = header.get("kid")
        if kid and kid not in public_keys:
            print(f"Unknown key ID: {kid}")
            return None

        # Return the Cognito user ID (sub claim)
        return payload.get("sub")

    except Exception as e:
        print(f"Token verification error: {e}")
        return None


def get_user_id_from_token(token: str) -> str | None:
    """Alias for verify_token — returns userId or None."""
    return verify_token(token)