import hashlib
import os
import secrets
import sqlite3


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{salt.hex()}:{derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, hash_hex = stored_hash.split(":")
    salt = bytes.fromhex(salt_hex)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return secrets.compare_digest(candidate.hex(), hash_hex)


def create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions(token, user_id) VALUES (?, ?)", (token, user_id))
    conn.commit()
    return token


def clear_session(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()

