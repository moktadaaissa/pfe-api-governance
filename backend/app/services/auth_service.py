import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.db_service import (
    get_user_by_username,
    get_user_by_id,
    record_login_attempt,
    count_recent_failed_attempts,
    save_refresh_token,
    get_refresh_token,
    revoke_refresh_token,
    revoke_all_user_refresh_tokens,
    update_last_login,
    write_audit_log,
)

_raw_secret = os.getenv("JWT_SECRET_KEY", "")
if not _raw_secret or len(_raw_secret) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing or too short (need ≥ 32 chars). "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
SECRET_KEY = _raw_secret

ACCESS_TOKEN_EXPIRY = 60 * 30              # 30 minutes
REFRESH_TOKEN_EXPIRY = 60 * 60 * 24 * 7    # 7 days
REFRESH_TOKEN_EXPIRY_LONG = 60 * 60 * 24 * 30  # 30 days (remember me)
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 900               # 15 minutes

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


# ─── Password Utilities ────────────────────────────────────────────────────────

def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), password_hash)


def validate_password_strength(password: str) -> list[str]:
    """Returns a list of issues. Empty list = password is acceptable."""
    issues = []
    if len(password) < 8:
        issues.append("Password must be at least 8 characters")
    if not re.search(r"[A-Za-z]", password):
        issues.append("Password must contain at least one letter")
    if not re.search(r"[0-9]", password):
        issues.append("Password must contain at least one number")
    return issues


def validate_username_format(username: str) -> list[str]:
    issues = []
    if len(username) < 3:
        issues.append("Username must be at least 3 characters")
    if len(username) > 32:
        issues.append("Username must be at most 32 characters")
    if not re.match(r"^[a-zA-Z0-9_\-]+$", username):
        issues.append("Username may only contain letters, numbers, underscores, and hyphens")
    return issues


# ─── JWT Utilities ─────────────────────────────────────────────────────────────

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(user: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + ACCESS_TOKEN_EXPIRY,
        "iat": int(time.time()),
    }
    header_encoded = _b64_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_encoded = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())
    message = f"{header_encoded}.{payload_encoded}".encode()
    signature = hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).digest()
    return f"{header_encoded}.{payload_encoded}.{_b64_encode(signature)}"


def create_refresh_token(user_id: int, remember_me: bool = False) -> tuple[str, int]:
    """Returns (raw_token, expires_at_timestamp)."""
    raw_token = secrets.token_urlsafe(48)
    expiry = REFRESH_TOKEN_EXPIRY_LONG if remember_me else REFRESH_TOKEN_EXPIRY
    expires_at = int(time.time()) + expiry
    save_refresh_token(user_id, raw_token, expires_at)
    return raw_token, expires_at


def decode_access_token(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed token")
        header_encoded, payload_encoded, signature_encoded = parts

        message = f"{header_encoded}.{payload_encoded}".encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).digest()
        received_sig = _b64_decode(signature_encoded)

        if not hmac.compare_digest(expected_sig, received_sig):
            raise HTTPException(status_code=401, detail="Invalid token signature")

        payload = json.loads(_b64_decode(payload_encoded))

        if payload.get("exp", 0) < int(time.time()):
            raise HTTPException(status_code=401, detail="Token expired")

        return payload

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# ─── Auth Logic ────────────────────────────────────────────────────────────────

def authenticate_user(username: str, password: str, ip_address: str = None):
    username = username.strip()

    # Rate limit check
    failed = count_recent_failed_attempts(username, LOCKOUT_WINDOW_SECONDS)
    if failed >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Please wait 15 minutes before trying again."
        )

    user = get_user_by_username(username)

    if not user or not user.get("password_hash") or not user.get("salt"):
        record_login_attempt(username, False, ip_address)
        return None

    if not user.get("is_active", 1):
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    if not verify_password(password, user["salt"], user["password_hash"]):
        record_login_attempt(username, False, ip_address)
        return None

    record_login_attempt(username, True, ip_address)
    update_last_login(user["id"])
    return user


def build_auth_response(user: dict, remember_me: bool = False) -> dict:
    """Build the standard token response returned on login/register/oauth."""
    access_token = create_access_token(user)
    refresh_token, refresh_expires = create_refresh_token(user["id"], remember_me=remember_me)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRY,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "email": user.get("email"),
            "avatar_url": user.get("avatar_url"),
            "oauth_provider": user.get("oauth_provider"),
        }
    }


def refresh_access_token(raw_refresh_token: str) -> dict:
    record = get_refresh_token(raw_refresh_token)

    if not record:
        raise HTTPException(status_code=401, detail="Refresh token not found")
    if record["revoked"]:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    if record["expires_at"] < int(time.time()):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = get_user_by_id(record["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate: revoke old, issue new
    revoke_refresh_token(raw_refresh_token)
    return build_auth_response(user)


# ─── FastAPI Dependencies ──────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    payload = decode_access_token(credentials.credentials)
    user_id = int(payload.get("sub", 0))
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active", 1):
        raise HTTPException(status_code=403, detail="Account deactivated")
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "email": user.get("email"),
        "avatar_url": user.get("avatar_url"),
        "oauth_provider": user.get("oauth_provider"),
        "email_verified": user.get("email_verified", 1),
        "created_at": user.get("created_at"),
    }


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only governance admins can perform this action")
    return current_user


# ─── Email helpers ─────────────────────────────────────────────────────────────

def generate_email_token() -> str:
    return secrets.token_urlsafe(32)


def send_verification_email(email: str, token: str, frontend_url: str):
    backend_url = os.getenv("BACKEND_URL", frontend_url)
    link = f"{backend_url}/verify-email?token={token}"
    try:
        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        email_from = os.getenv("EMAIL_FROM", "")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify your API Governance account"
        msg["From"] = email_from
        msg["To"] = email
        msg.attach(MIMEText(f"""
                <div style="font-family:Inter,sans-serif;max-width:480px;
                margin:0 auto;padding:40px 24px">
                  <h2 style="font-size:24px;font-weight:900;color:#101827;
                  letter-spacing:-0.04em;margin:0 0 8px">
                    Verify your email</h2>
                  <p style="color:#44546a;font-size:16px;line-height:1.7;
                  margin:0 0 28px">
                    Click the button below to activate your account on the
                    BIAT API Governance Platform.</p>
                  <a href="{link}" style="display:inline-block;
                  background:#245fe6;color:white;font-weight:900;
                  font-size:15px;padding:14px 28px;border-radius:999px;
                  text-decoration:none">Verify my account</a>
                  <p style="color:#73839a;font-size:13px;margin:28px 0 0">
                    This link expires in 24 hours. If you did not create
                    this account, ignore this email.</p>
                </div>""", "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, email, msg.as_string())
    except Exception as e:
        logger.error("send_verification_email failed: %s", e)
        pass  # Email delivery failure must not crash registration


def send_password_reset_email(email: str, token: str, frontend_url: str):
    backend_url = os.getenv("BACKEND_URL", frontend_url)
    link = f"{backend_url}/reset-password?token={token}"
    try:
        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        email_from = os.getenv("EMAIL_FROM", "")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your password — API Governance"
        msg["From"] = email_from
        msg["To"] = email
        msg.attach(MIMEText(f"""
                <div style="font-family:Inter,sans-serif;max-width:480px;
                margin:0 auto;padding:40px 24px">
                  <h2 style="font-size:24px;font-weight:900;color:#101827;
                  letter-spacing:-0.04em;margin:0 0 8px">
                    Reset your password</h2>
                  <p style="color:#44546a;font-size:16px;line-height:1.7;
                  margin:0 0 28px">
                    We received a request to reset your password.
                    Click below to choose a new one.</p>
                  <a href="{link}" style="display:inline-block;
                  background:#245fe6;color:white;font-weight:900;
                  font-size:15px;padding:14px 28px;border-radius:999px;
                  text-decoration:none">Reset my password</a>
                  <p style="color:#73839a;font-size:13px;margin:28px 0 0">
                    This link expires in 15 minutes. If you did not request
                    this, ignore this email.</p>
                </div>""", "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, email, msg.as_string())
    except Exception as e:
        logger.error("send_password_reset_email failed: %s", e)
        pass  # Email delivery failure must not crash the endpoint