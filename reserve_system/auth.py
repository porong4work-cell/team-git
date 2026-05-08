import secrets
import uuid
from hashlib import pbkdf2_hmac

from config import PBKDF2_ITERATIONS
from db import connect_db, now_text


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_bytes(16)
    derived = pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_hex, expected_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return secrets.compare_digest(actual.hex(), expected_hex)
    except (TypeError, ValueError):
        return False


def public_user(user):
    return {
        "id": user["id"],
        "studentId": user["student_id"],
        "name": user["name"],
    }


def validate_signup(payload):
    student_id = str(payload.get("studentId", "")).strip()
    name = str(payload.get("name", "")).strip()
    password = str(payload.get("password", ""))

    if not student_id or not student_id.isdigit():
        return "학번은 숫자로 입력하세요."
    if not name:
        return "이름을 입력하세요."
    if len(password) < 4:
        return "비밀번호는 4자 이상 입력하세요."
    return ""


def create_user(payload):
    user = {
        "id": str(uuid.uuid4()),
        "student_id": str(payload.get("studentId", "")).strip(),
        "name": str(payload.get("name", "")).strip(),
        "password_hash": hash_password(str(payload.get("password", ""))),
        "created_at": now_text(),
    }
    with connect_db() as db:
        db.execute(
            """
            INSERT INTO users (id, student_id, name, password_hash, created_at)
            VALUES (:id, :student_id, :name, :password_hash, :created_at)
            """,
            user,
        )
    return user


def find_user_by_student_id(student_id):
    with connect_db() as db:
        return db.execute(
            "SELECT * FROM users WHERE student_id = ?",
            (str(student_id).strip(),),
        ).fetchone()


def find_user_by_session(token):
    if not token:
        return None
    with connect_db() as db:
        return db.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    with connect_db() as db:
        db.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, now_text()),
        )
    return token


def delete_session(token):
    if not token:
        return
    with connect_db() as db:
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))
