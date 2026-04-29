import base64
import hashlib
import hmac
import json
import os
import time
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.db_service import get_user_by_username

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-key-for-pfe-demo")
TOKEN_EXPIRATION_SECONDS = 60 * 60 * 8

security = HTTPBearer()


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), password_hash)


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(user: dict) -> str:
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }

    payload = {
        "sub": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + TOKEN_EXPIRATION_SECONDS
    }

    header_encoded = _b64_encode(json.dumps(header).encode())
    payload_encoded = _b64_encode(json.dumps(payload).encode())

    message = f"{header_encoded}.{payload_encoded}".encode()
    signature = hmac.new(
        SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).digest()

    signature_encoded = _b64_encode(signature)

    return f"{header_encoded}.{payload_encoded}.{signature_encoded}"


def decode_access_token(token: str) -> dict:
    try:
        header_encoded, payload_encoded, signature_encoded = token.split(".")

        message = f"{header_encoded}.{payload_encoded}".encode()
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            message,
            hashlib.sha256
        ).digest()

        received_signature = _b64_decode(signature_encoded)

        if not hmac.compare_digest(expected_signature, received_signature):
            raise HTTPException(status_code=401, detail="Invalid token signature")

        payload = json.loads(_b64_decode(payload_encoded))

        if payload.get("exp", 0) < int(time.time()):
            raise HTTPException(status_code=401, detail="Token expired")

        return payload

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def authenticate_user(username: str, password: str):
    user = get_user_by_username(username)

    if not user:
        return None

    if not verify_password(password, user["salt"], user["password_hash"]):
        return None

    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    payload = decode_access_token(credentials.credentials)

    username = payload.get("sub")
    user = get_user_by_username(username)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"]
    }


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only governance admins can perform this action"
        )

    return current_user