import sqlite3
from pathlib import Path
from typing import Any
import os

BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "apis.db"


def get_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str, salt: str) -> str:
    import hashlib
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()


def _create_default_user(cursor, username: str, password: str, role: str):
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    existing = cursor.fetchone()

    if existing:
        return

    salt = os.urandom(16).hex()
    password_hash = _hash_password(password, salt)

    cursor.execute(
        """
        INSERT INTO users (username, password_hash, salt, role)
        VALUES (?, ?, ?, ?)
        """,
        (username, password_hash, salt, role)
    )


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
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('developer', 'admin')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    _create_default_user(cursor, "admin", "admin123", "admin")
    _create_default_user(cursor, "developer", "dev123", "developer")

    conn.commit()
    conn.close()


def get_user_by_username(username: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, username, password_hash, salt, role
        FROM users
        WHERE username = ?
        """,
        (username,)
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


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


def save_api_to_catalog(data: dict, filename: str) -> int:
    info = data.get("info", {}) if isinstance(data, dict) else {}
    title = info.get("title", "") if isinstance(info, dict) else ""
    version = info.get("version", "") if isinstance(info, dict) else ""

    endpoints = extract_endpoints(data)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO apis (filename, title, version)
        VALUES (?, ?, ?)
        """,
        (filename, title, version)
    )

    api_id = cursor.lastrowid

    for ep in endpoints:
        cursor.execute(
            """
            INSERT INTO endpoints (
                api_id, path, method, summary, description, operation_id, tags
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
    conn.close()

    return api_id


def list_catalog_apis() -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, filename, title, version, uploaded_at
    FROM apis
    ORDER BY uploaded_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]