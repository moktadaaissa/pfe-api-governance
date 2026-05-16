import os
import re
import secrets
import httpx
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

from app.services.auth_service import (
    authenticate_user,
    build_auth_response,
    refresh_access_token,
    revoke_refresh_token,
    revoke_all_user_refresh_tokens,
    get_current_user,
    require_admin,
    validate_password_strength,
    validate_username_format,
    create_access_token,
    create_refresh_token,
    generate_email_token,
    send_verification_email,
    send_password_reset_email,
    hash_password,
    verify_password,
)
from app.services.db_service import (
    create_user,
    get_or_create_oauth_user,
    get_user_by_username,
    list_all_users,
    update_user_role,
    write_audit_log,
    get_audit_log,
    get_user_by_id,
    get_user_by_email,
    set_email_verification_token,
    get_user_by_verification_token,
    confirm_email_verification,
    set_password_reset_token,
    get_user_by_reset_token,
    reset_user_password,
    get_login_history_by_username,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://repair-remember-dismount.ngrok-free.dev")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/auth/github/callback")


# ─── Request / Response Models ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8)
    email: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UpdateRoleRequest(BaseModel):
    role: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ─── Standard Auth ─────────────────────────────────────────────────────────────

@router.post("/login")
def login(payload: LoginRequest, request: Request):
    ip = request.client.host if request.client else None

    username_issues = validate_username_format(payload.username.strip())
    if username_issues:
        raise HTTPException(status_code=422, detail=username_issues[0])

    user = authenticate_user(payload.username, payload.password, ip_address=ip)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Block unverified email accounts (OAuth users are always verified)
    if not user.get("oauth_provider") and user.get("email_verified") == 0:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in."
        )

    write_audit_log("login", "Successful login", user_id=user["id"], username=user["username"], ip_address=ip)
    return build_auth_response(user, remember_me=payload.remember_me)


@router.post("/register")
def register(payload: RegisterRequest, request: Request):
    ip = request.client.host if request.client else None
    username = payload.username.strip()
    email = payload.email.strip() if payload.email else ""

    username_issues = validate_username_format(username)
    if username_issues:
        raise HTTPException(status_code=422, detail=username_issues[0])

    if not email or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    password_issues = validate_password_strength(payload.password)
    if password_issues:
        raise HTTPException(status_code=422, detail=password_issues[0])

    user = create_user(username=username, password=payload.password, role="developer", email=email)
    if not user:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    token = generate_email_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    set_email_verification_token(user["id"], token, expires_at)
    send_verification_email(email, token, FRONTEND_URL)

    write_audit_log("register", "New account created", user_id=user["id"], username=username, ip_address=ip)
    return {"message": "Check your email to verify your account."}


@router.post("/refresh")
def refresh(payload: RefreshRequest):
    return refresh_access_token(payload.refresh_token)


@router.post("/logout")
def logout(payload: LogoutRequest, current_user: dict = Depends(get_current_user)):
    revoke_refresh_token(payload.refresh_token)
    write_audit_log("logout", "User logged out", user_id=current_user["id"], username=current_user["username"])
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
def logout_all(current_user: dict = Depends(get_current_user)):
    revoke_all_user_refresh_tokens(current_user["id"])
    write_audit_log("logout_all", "All sessions revoked", user_id=current_user["id"], username=current_user["username"])
    return {"message": "All sessions revoked"}


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user


# ─── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google")
def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured")
    state = secrets.token_urlsafe(16)
    params = (
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
        f"&state={state}"
    )
    resp = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")
    resp.set_cookie("oauth_state", state, httponly=True, samesite="lax", max_age=300)
    return resp


@router.get("/google/callback")
async def google_callback(code: str, state: str, request: Request):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured")
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not secrets.compare_digest(stored_state, state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange Google code")

        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        # Get user info from Google
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get Google user info")

        google_user = userinfo_resp.json()

    user = get_or_create_oauth_user(
        provider="google",
        oauth_id=google_user["id"],
        username=google_user.get("name", "").replace(" ", "_").lower() or "user",
        email=google_user.get("email"),
        avatar_url=google_user.get("picture"),
    )

    ip = request.client.host if request.client else None
    write_audit_log("oauth_login", "Google OAuth login", user_id=user["id"], username=user["username"], ip_address=ip)

    auth_data = build_auth_response(user)
    access = auth_data["access_token"]
    refresh = auth_data["refresh_token"]
    # Use fragment (#) so tokens are never sent to the server or logged
    return RedirectResponse(
        f"{FRONTEND_URL}/oauth-callback#access_token={access}&refresh_token={refresh}",
        status_code=302,
    )


# ─── GitHub OAuth ──────────────────────────────────────────────────────────────

@router.get("/github")
def github_login():
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")
    state = secrets.token_urlsafe(16)
    params = (
        f"client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=read:user%20user:email"
        f"&state={state}"
    )
    resp = RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")
    resp.set_cookie("oauth_state", state, httponly=True, samesite="lax", max_age=300)
    return resp


@router.get("/github/callback")
async def github_callback(code: str, state: str, request: Request):
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not secrets.compare_digest(stored_state, state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            }
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to exchange GitHub code")

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        github_user = user_resp.json()

        email_resp = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        emails = email_resp.json()
        primary_email = next((e["email"] for e in emails if e.get("primary")), None)

    user = get_or_create_oauth_user(
        provider="github",
        oauth_id=str(github_user["id"]),
        username=github_user.get("login", "user"),
        email=primary_email or github_user.get("email"),
        avatar_url=github_user.get("avatar_url"),
    )

    ip = request.client.host if request.client else None
    write_audit_log("oauth_login", "GitHub OAuth login", user_id=user["id"], username=user["username"], ip_address=ip)

    auth_data = build_auth_response(user)
    access = auth_data["access_token"]
    refresh = auth_data["refresh_token"]
    return RedirectResponse(
        f"{FRONTEND_URL}/oauth-callback#access_token={access}&refresh_token={refresh}"
    )


# ─── Admin: User Management ────────────────────────────────────────────────────

@router.get("/users")
def get_all_users(current_user: dict = Depends(require_admin)):
    return {"users": list_all_users()}


@router.patch("/users/{user_id}/role")
def change_user_role(user_id: int, payload: UpdateRoleRequest, current_user: dict = Depends(require_admin)):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    success = update_user_role(user_id, payload.role)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid role or user not found")
    target = get_user_by_id(user_id)
    write_audit_log(
        "role_change",
        f"Changed user {user_id} role to {payload.role}",
        user_id=current_user["id"],
        username=current_user["username"]
    )
    return {"message": f"Role updated to {payload.role}", "user": target}


@router.get("/audit-log")
def audit_log(
    limit: int = 50,
    offset: int = 0,
    _: dict = Depends(require_admin),
):
    limit = min(max(1, limit), 200)
    return {"logs": get_audit_log(limit=limit, offset=offset), "limit": limit, "offset": offset}


# ─── Email Verification ────────────────────────────────────────────────────────

@router.get("/confirm-email", response_class=HTMLResponse)
def confirm_email(token: str):
    from app.services.db_service import get_user_by_verification_token, confirm_email_verification
    user = get_user_by_verification_token(token)
    if not user:
        return HTMLResponse(content="""
        <html><head><title>Invalid Link</title></head>
        <body style="font-family:Inter,sans-serif;max-width:480px;margin:80px auto;padding:40px 24px;text-align:center">
          <div style="font-size:48px">✗</div>
          <h2 style="color:#ef4444;font-size:24px;font-weight:900">Invalid Link</h2>
          <p style="color:#44546a">This verification link is invalid or has already been used.</p>
        </body></html>""", status_code=400)

    expires_at_str = user.get("email_verification_expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                return HTMLResponse(content="""
                <html><head><title>Link Expired</title></head>
                <body style="font-family:Inter,sans-serif;max-width:480px;margin:80px auto;padding:40px 24px;text-align:center">
                  <div style="font-size:48px">⏱</div>
                  <h2 style="color:#f97316;font-size:24px;font-weight:900">Link Expired</h2>
                  <p style="color:#44546a">This verification link has expired. Please register again.</p>
                </body></html>""", status_code=400)
        except ValueError:
            return HTMLResponse(content="Invalid link.", status_code=400)

    confirm_email_verification(user["id"])
    return HTMLResponse(content="""
    <html><head><title>Account Verified</title></head>
    <body style="font-family:Inter,sans-serif;max-width:480px;margin:80px auto;padding:40px 24px;text-align:center">
      <div style="font-size:48px;color:#22c55e">✓</div>
      <h2 style="color:#101827;font-size:24px;font-weight:900;margin:16px 0 8px">Account created successfully!</h2>
      <p style="color:#44546a;font-size:16px;line-height:1.7">Your email has been verified. You can now sign in to the API Governance Platform.</p>
    </body></html>""")


@router.get("/verify-email")
def verify_email(token: str):
    user = get_user_by_verification_token(token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification link.")

    expires_at_str = user.get("email_verification_expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(status_code=400, detail="Verification link has expired.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid verification link.")

    if user.get("email_verified"):
        return {"verified": True, "message": "Email already verified."}

    confirm_email_verification(user["id"])
    return {"verified": True}


# ─── Forgot / Reset Password ───────────────────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.strip() if payload.email else ""
    # Always return the same response to prevent email enumeration
    _SAFE_MSG = {"message": "If this email is registered, you will receive a reset link."}

    if not email or not _EMAIL_RE.match(email):
        return _SAFE_MSG

    user = get_user_by_email(email)
    if not user:
        return _SAFE_MSG

    token = generate_email_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    set_password_reset_token(user["id"], token, expires_at)
    send_password_reset_email(email, token, FRONTEND_URL)

    return _SAFE_MSG


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    user = get_user_by_reset_token(payload.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    expires_at_str = user.get("password_reset_expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(status_code=400, detail="Reset link has expired.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid reset link.")

    pw_issues = validate_password_strength(payload.new_password)
    if pw_issues:
        raise HTTPException(status_code=422, detail=pw_issues[0])

    import os as _os
    new_salt = _os.urandom(16).hex()
    new_hash = hash_password(payload.new_password, new_salt)
    reset_user_password(user["id"], new_hash, new_salt)
    revoke_all_user_refresh_tokens(user["id"])

    return {"reset": True}


# ─── Change Password ───────────────────────────────────────────────────────────

@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    full_user = get_user_by_username(current_user["username"])
    if not full_user or not full_user.get("password_hash") or not full_user.get("salt"):
        raise HTTPException(status_code=400, detail="Cannot change password for OAuth accounts.")

    if not verify_password(payload.current_password, full_user["salt"], full_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    pw_issues = validate_password_strength(payload.new_password)
    if pw_issues:
        raise HTTPException(status_code=422, detail=pw_issues[0])

    import os as _os
    new_salt = _os.urandom(16).hex()
    new_hash = hash_password(payload.new_password, new_salt)
    reset_user_password(current_user["id"], new_hash, new_salt)
    revoke_all_user_refresh_tokens(current_user["id"])

    write_audit_log("change_password", "Password changed", user_id=current_user["id"], username=current_user["username"])
    return {"changed": True}


# ─── Login History ─────────────────────────────────────────────────────────────

@router.get("/login-history")
def login_history(current_user: dict = Depends(get_current_user)):
    history = get_login_history_by_username(current_user["username"], limit=10)
    return {"history": history}