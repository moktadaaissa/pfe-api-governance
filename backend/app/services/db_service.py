import sqlite3
from pathlib import Path
from typing import Any
import os
import hashlib

BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "apis.db"


def get_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row["name"] == column_name for row in cursor.fetchall())


def _ensure_user_columns(cursor):
    new_columns = {
        "email_verification_token": "TEXT",
        "email_verified": "INTEGER DEFAULT 0",
        "email_verification_expires_at": "TEXT",
        "password_reset_token": "TEXT",
        "password_reset_expires_at": "TEXT",
    }
    for column, column_type in new_columns.items():
        if not _column_exists(cursor, "users", column):
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {column_type}")
            if column == "email_verified":
                # Grandfather all pre-existing accounts as verified so logins aren't broken
                cursor.execute("UPDATE users SET email_verified = 1")


def _ensure_catalog_columns(cursor):
    new_columns = {
        "published_by_user_id": "INTEGER",
        "published_by_username": "TEXT",
        "published_by_role": "TEXT",
        "apri_score": "REAL",
        "grade": "TEXT",
        "status": "TEXT",
        "governance_decision": "TEXT",
        "published_at": "TIMESTAMP",
        "wso2_api_id": "TEXT",
    }

    for column, column_type in new_columns.items():
        if not _column_exists(cursor, "apis", column):
            cursor.execute(f"ALTER TABLE apis ADD COLUMN {column} {column_type}")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        title TEXT,
        version TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS endpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_id INTEGER NOT NULL,
        path TEXT NOT NULL,
        method TEXT NOT NULL,
        summary TEXT,
        description TEXT,
        operation_id TEXT,
        tags TEXT,
        FOREIGN KEY (api_id) REFERENCES apis(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT UNIQUE,
        password_hash TEXT,
        salt TEXT,
        role TEXT NOT NULL DEFAULT 'developer' CHECK(role IN ('developer', 'admin')),
        oauth_provider TEXT,
        oauth_id TEXT,
        avatar_url TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        revoked INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        ip_address TEXT,
        success INTEGER NOT NULL DEFAULT 0,
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        action TEXT NOT NULL,
        detail TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    _ensure_catalog_columns(cursor)
    _ensure_user_columns(cursor)

    conn.commit()
    conn.close()


# ─── User CRUD ────────────────────────────────────────────────────────────────

def create_user(username: str, password: str, role: str = "developer", email: str = None):
    username = username.strip()
    if not username:
        return None
    if role not in {"developer", "admin"}:
        role = "developer"
    if get_user_by_username(username):
        return None

    salt = os.urandom(16).hex()
    password_hash = _hash_password(password, salt)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, salt, role)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return {"id": user_id, "username": username, "role": role, "email": email}
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_or_create_oauth_user(provider: str, oauth_id: str, username: str, email: str, avatar_url: str = None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, email, role, avatar_url, oauth_provider FROM users WHERE oauth_provider = ? AND oauth_id = ?",
        (provider, oauth_id)
    )
    row = cursor.fetchone()

    if row:
        cursor.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP, avatar_url = ? WHERE id = ?",
            (avatar_url, row["id"])
        )
        conn.commit()
        conn.close()
        return dict(row)

    base_username = username[:28]  # leave room for _NNN suffix
    counter = 1
    while True:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            break
        if counter > 99:
            import secrets as _s
            username = f"{base_username}_{_s.token_hex(3)}"
            break
        username = f"{base_username}_{counter}"
        counter += 1

    cursor.execute(
        """INSERT INTO users (username, email, oauth_provider, oauth_id, avatar_url, role, email_verified)
           VALUES (?, ?, ?, ?, ?, 'developer', 1)""",
        (username, email, provider, oauth_id, avatar_url)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"id": user_id, "username": username, "email": email, "role": "developer", "avatar_url": avatar_url}


def get_user_by_username(username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, password_hash, salt, role, avatar_url, oauth_provider, is_active, email_verified FROM users WHERE username = ?",
        (username,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, role, avatar_url, oauth_provider, is_active, email_verified, created_at, last_login_at FROM users WHERE id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def list_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, role, oauth_provider, avatar_url, is_active, created_at, last_login_at FROM users ORDER BY created_at DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user_role(user_id: int, new_role: str):
    if new_role not in {"developer", "admin"}:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    return True


def update_last_login(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


# ─── Email Verification & Password Reset ──────────────────────────────────────

def get_user_by_email(email: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, role, avatar_url, oauth_provider, is_active, email_verified FROM users WHERE email = ?",
        (email,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def set_email_verification_token(user_id: int, token: str, expires_at: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET email_verification_token = ?, email_verification_expires_at = ? WHERE id = ?",
        (token, expires_at, user_id)
    )
    conn.commit()
    conn.close()


def get_user_by_verification_token(token: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, role, email_verified, email_verification_expires_at FROM users WHERE email_verification_token = ?",
        (token,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def confirm_email_verification(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET email_verified = 1 WHERE id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


def set_password_reset_token(user_id: int, token: str, expires_at: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_reset_token = ?, password_reset_expires_at = ? WHERE id = ?",
        (token, expires_at, user_id)
    )
    conn.commit()
    conn.close()


def get_user_by_reset_token(token: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, role, password_reset_expires_at FROM users WHERE password_reset_token = ?",
        (token,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def reset_user_password(user_id: int, new_hash: str, new_salt: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ?, salt = ?, password_reset_token = NULL, password_reset_expires_at = NULL WHERE id = ?",
        (new_hash, new_salt, user_id)
    )
    conn.commit()
    conn.close()


def get_login_history_by_username(username: str, limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT attempted_at, success, ip_address FROM login_attempts WHERE username = ? ORDER BY attempted_at DESC LIMIT ?",
        (username, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Login Rate Limiting ───────────────────────────────────────────────────────

def record_login_attempt(username: str, success: bool, ip_address: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO login_attempts (username, ip_address, success) VALUES (?, ?, ?)",
        (username, ip_address, 1 if success else 0)
    )
    conn.commit()
    conn.close()


def count_recent_failed_attempts(username: str, window_seconds: int = 900) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COUNT(*) as cnt FROM login_attempts
           WHERE username = ? AND success = 0
           AND attempted_at >= datetime('now', ? || ' seconds')""",
        (username, f"-{window_seconds}")
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ─── Refresh Tokens ────────────────────────────────────────────────────────────

def save_refresh_token(user_id: int, token: str, expires_at: int):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (user_id, token_hash, expires_at)
    )
    conn.commit()
    conn.close()


def get_refresh_token(token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, expires_at, revoked FROM refresh_tokens WHERE token_hash = ?",
        (token_hash,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def revoke_refresh_token(token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,))
    conn.commit()
    conn.close()


def revoke_all_user_refresh_tokens(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ─── Audit Log ────────────────────────────────────────────────────────────────

def write_audit_log(action: str, detail: str = None, user_id: int = None, username: str = None, ip_address: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_log (user_id, username, action, detail, ip_address) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, action, detail, ip_address)
    )
    conn.commit()
    conn.close()


def get_audit_log(limit: int = 50, offset: int = 0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── API Catalog ───────────────────────────────────────────────────────────────

def ensure_catalog_columns():
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_catalog_columns(cursor)
    conn.commit()
    conn.close()


def extract_endpoints(data: dict) -> list[dict[str, Any]]:
    valid_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    valid_path_level_fields = {"parameters", "summary", "description", "servers"}
    endpoints = []

    paths = data.get("paths", {})
    if not isinstance(paths, dict):
        return endpoints

    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue

        for method, details in methods.items():
            if method in valid_path_level_fields:
                continue

            method_lower = str(method).lower()
            if method_lower not in valid_methods:
                continue

            if not isinstance(details, dict):
                continue

            endpoints.append({
                "path": path,
                "method": method_lower,
                "summary": details.get("summary", "") or "",
                "description": details.get("description", "") or "",
                "operation_id": details.get("operationId", "") or "",
                "tags": ",".join(details.get("tags", [])) if isinstance(details.get("tags"), list) else ""
            })

    return endpoints


def save_api_to_catalog(
    data: dict,
    filename: str,
    current_user: dict,
    apri_result: dict,
    status: str,
    governance_decision: str,
    wso2_api_id: str = None,
) -> int:
    ensure_catalog_columns()

    info = data.get("info", {}) if isinstance(data, dict) else {}
    title = info.get("title", "") if isinstance(info, dict) else ""
    version = info.get("version", "") if isinstance(info, dict) else ""
    endpoints = extract_endpoints(data)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO apis (
                filename,
                title,
                version,
                published_by_user_id,
                published_by_username,
                published_by_role,
                apri_score,
                grade,
                status,
                governance_decision,
                wso2_api_id,
                published_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                filename,
                title,
                version,
                current_user.get("id"),
                current_user.get("username"),
                current_user.get("role"),
                apri_result.get("apri_score"),
                apri_result.get("grade"),
                status,
                governance_decision,
                wso2_api_id,
            )
        )

        api_id = cursor.lastrowid

        for ep in endpoints:
            cursor.execute(
                """
                INSERT INTO endpoints (
                    api_id,
                    path,
                    method,
                    summary,
                    description,
                    operation_id,
                    tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    api_id,
                    ep["path"],
                    ep["method"],
                    ep["summary"],
                    ep["description"],
                    ep["operation_id"],
                    ep["tags"],
                )
            )

        conn.commit()
        return api_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_catalog_apis() -> list[dict[str, Any]]:
    ensure_catalog_columns()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            filename,
            title,
            version,
            published_by_user_id,
            published_by_username,
            published_by_role,
            apri_score,
            grade,
            status,
            governance_decision,
            wso2_api_id,
            COALESCE(published_at, uploaded_at) AS published_at,
            uploaded_at
        FROM apis
        ORDER BY COALESCE(published_at, uploaded_at) DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_api_from_catalog(api_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM apis WHERE id = ?", (api_id,))
    existing = cursor.fetchone()

    if not existing:
        conn.close()
        return False

    cursor.execute("DELETE FROM endpoints WHERE api_id = ?", (api_id,))
    cursor.execute("DELETE FROM apis WHERE id = ?", (api_id,))

    conn.commit()
    conn.close()
    return True