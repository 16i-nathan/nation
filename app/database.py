import os
import sqlite3
from pathlib import Path


def get_db_path() -> str:
    configured = os.getenv("LEARNING_DB_PATH")
    if configured:
        return configured
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "learning.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'lecturer', 'student')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            lecturer_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(lecturer_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(course_id, student_id),
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content_url TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            instructions TEXT NOT NULL,
            due_date TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(assignment_id, student_id),
            FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
            FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()
