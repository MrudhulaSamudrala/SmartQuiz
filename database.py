"""
SQLite database layer for quiz attempt history.
Designed for future analytics (dashboards, weak topics, recommendations).
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from config import DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                topic TEXT NOT NULL,
                quiz_type TEXT NOT NULL,
                quiz_mode TEXT NOT NULL,
                quiz_source TEXT,
                difficulty TEXT,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                accuracy REAL NOT NULL,
                date_time TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS question_history (
                question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_index INTEGER NOT NULL,
                question_type TEXT NOT NULL,
                question TEXT NOT NULL,
                options_json TEXT,
                user_answer TEXT,
                correct_answer TEXT NOT NULL,
                explanation TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(attempt_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_attempts_student
                ON quiz_attempts(student_name);
            CREATE INDEX IF NOT EXISTS idx_attempts_datetime
                ON quiz_attempts(date_time DESC);
            CREATE INDEX IF NOT EXISTS idx_questions_attempt
                ON question_history(attempt_id);
            """
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def insert_quiz_attempt(
    student_name: str,
    topic: str,
    quiz_type: str,
    quiz_mode: str,
    quiz_source: str | None,
    difficulty: str | None,
    score: int,
    total_questions: int,
    accuracy: float,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO quiz_attempts (
                student_name, topic, quiz_type, quiz_mode, quiz_source,
                difficulty, score, total_questions, accuracy, date_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_name,
                topic,
                quiz_type,
                quiz_mode,
                quiz_source,
                difficulty,
                score,
                total_questions,
                accuracy,
                _utc_now_iso(),
            ),
        )
        return int(cursor.lastrowid)


def insert_question_history(
    attempt_id: int,
    question_index: int,
    question_type: str,
    question: str,
    options_json: str | None,
    user_answer: str | None,
    correct_answer: str,
    explanation: str,
    is_correct: bool,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO question_history (
                attempt_id, question_index, question_type, question,
                options_json, user_answer, correct_answer, explanation, is_correct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                question_index,
                question_type,
                question,
                options_json,
                user_answer,
                correct_answer,
                explanation,
                1 if is_correct else 0,
            ),
        )


def list_quiz_attempts(student_name: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    query = """
        SELECT attempt_id, student_name, topic, quiz_type, quiz_mode,
               quiz_source, difficulty, score, total_questions, accuracy, date_time
        FROM quiz_attempts
    """
    params: list[Any] = []

    if student_name:
        query += " WHERE student_name = ?"
        params.append(student_name.strip())

    query += " ORDER BY attempt_id DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_quiz_attempt(attempt_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM quiz_attempts WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchone()
    return dict(row) if row else None


def get_questions_for_attempt(attempt_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM question_history
            WHERE attempt_id = ?
            ORDER BY question_index ASC
            """,
            (attempt_id,),
        ).fetchall()

    results = []
    for row in rows:
        item = dict(row)
        if item.get("options_json"):
            try:
                item["options"] = json.loads(item["options_json"])
            except json.JSONDecodeError:
                item["options"] = []
        else:
            item["options"] = None
        item["is_correct"] = bool(item["is_correct"])
        results.append(item)
    return results


def delete_attempt(attempt_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM question_history WHERE attempt_id = ?", (attempt_id,))
        conn.execute("DELETE FROM quiz_attempts WHERE attempt_id = ?", (attempt_id,))
