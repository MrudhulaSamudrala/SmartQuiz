"""
Business logic for saving and retrieving quiz attempt history.
"""

import json
from typing import Any

import streamlit as st

from database import (
    get_questions_for_attempt,
    get_quiz_attempt,
    init_db,
    insert_question_history,
    insert_quiz_attempt,
    list_quiz_attempts,
)
from quiz_scoring import (
    calculate_score,
    format_correct_answer,
    format_user_answer,
    is_correct,
)
from session_state import get_student_name, persist_student_name_backup


def ensure_database() -> None:
    init_db()


def _topic_from_session() -> str:
    label = st.session_state.get("source_label") or ""
    if label:
        return label
    return st.session_state.get("quiz_source") or "Quiz"


def _build_question_rows(quiz: list[dict], answers: dict) -> list[dict[str, Any]]:
    rows = []
    for i, q in enumerate(quiz):
        user_raw = answers.get(i)
        rows.append(
            {
                "question_index": i,
                "question_type": q.get("type", ""),
                "question": q["question"],
                "options_json": json.dumps(q["options"]) if q.get("options") else None,
                "user_answer": format_user_answer(q, user_raw) if user_raw is not None else None,
                "correct_answer": format_correct_answer(q),
                "explanation": q.get("explanation", ""),
                "is_correct": is_correct(q, user_raw),
            }
        )
    return rows


def save_attempt_from_session() -> int | None:
    """
    Persist the current completed quiz to SQLite.
    Returns attempt_id or None if already saved / missing data.
    """
    if st.session_state.get("attempt_saved"):
        return st.session_state.get("last_attempt_id")

    quiz = st.session_state.get("quiz_data")
    if not quiz:
        return None

    persist_student_name_backup()
    student_name = get_student_name()
    if not student_name:
        return None

    answers = st.session_state.get("answers") or {}
    score, total, _ = calculate_score(quiz, answers)
    accuracy = round(100 * score / total, 1) if total else 0.0

    ensure_database()

    attempt_id = insert_quiz_attempt(
        student_name=student_name,
        topic=_topic_from_session(),
        quiz_type=st.session_state.get("quiz_type") or "",
        quiz_mode=st.session_state.get("quiz_mode") or "",
        quiz_source=st.session_state.get("quiz_source"),
        difficulty=st.session_state.get("difficulty"),
        score=score,
        total_questions=total,
        accuracy=accuracy,
    )

    for row in _build_question_rows(quiz, answers):
        insert_question_history(
            attempt_id=attempt_id,
            question_index=row["question_index"],
            question_type=row["question_type"],
            question=row["question"],
            options_json=row["options_json"],
            user_answer=row["user_answer"],
            correct_answer=row["correct_answer"],
            explanation=row["explanation"],
            is_correct=row["is_correct"],
        )

    st.session_state.attempt_saved = True
    st.session_state.last_attempt_id = attempt_id
    return attempt_id


def fetch_attempt_summaries(student_name: str | None = None) -> list[dict[str, Any]]:
    ensure_database()
    return list_quiz_attempts(student_name=student_name)


def fetch_attempt_detail(attempt_id: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ensure_database()
    attempt = get_quiz_attempt(attempt_id)
    if not attempt:
        return None, []
    questions = get_questions_for_attempt(attempt_id)
    return attempt, questions
