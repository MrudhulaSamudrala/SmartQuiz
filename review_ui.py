"""
UI for quiz history list and detailed attempt review.
"""

import streamlit as st

from config import TYPE_LABELS
from history_service import fetch_attempt_detail, fetch_attempt_summaries
from session_state import get_student_name


def open_history_view():
    st.session_state.show_history = True
    st.session_state.view_attempt_id = None


def open_attempt_review(attempt_id: int):
    st.session_state.view_attempt_id = attempt_id
    st.session_state.show_history = False


def close_history_views():
    st.session_state.show_history = False
    st.session_state.view_attempt_id = None


def render_history_list():
    st.subheader("Quiz History")
    st.caption("Review past attempts to revise questions and explanations.")

    filter_name = get_student_name()
    col1, col2 = st.columns([3, 1])
    with col1:
        search_name = st.text_input(
            "Filter by student name",
            value=filter_name,
            placeholder="Leave blank to show all students",
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("Refresh", use_container_width=True):
            st.rerun()

    attempts = fetch_attempt_summaries(search_name if search_name else None)

    if not attempts:
        st.info("No quiz attempts found yet. Complete a quiz to build your history.")
        if st.button("← Back to Home"):
            close_history_views()
            st.rerun()
        return

    for att in attempts:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**{att['topic']}**")
                st.caption(
                    f"{att['student_name']} · {att['quiz_type']} · {att['quiz_mode']} · "
                    f"{att['date_time']}"
                )
                st.progress(att["accuracy"] / 100, text=f"Score: {att['score']}/{att['total_questions']} ({att['accuracy']}%)")
            with c2:
                if st.button("Review", key=f"review_{att['attempt_id']}", use_container_width=True):
                    open_attempt_review(att["attempt_id"])
                    st.rerun()

    st.divider()
    if st.button("← Back to Home", use_container_width=True):
        close_history_views()
        st.rerun()


def _render_question_card(q: dict, number: int):
    is_ok = q["is_correct"]
    status = "Correct" if is_ok else "Incorrect"
    icon = "✅" if is_ok else "❌"

    with st.expander(f"{icon} Q{number} — {status}", expanded=not is_ok):
        st.markdown(f"**{q['question']}**")
        qtype = q.get("question_type", "")
        st.caption(f"Type: {TYPE_LABELS.get(qtype, qtype)}")

        options = q.get("options")
        if options:
            for i, opt in enumerate(options):
                st.markdown(f"- {chr(65 + i)}. {opt}")

        u = q.get("user_answer") or "No answer"
        c = q.get("correct_answer") or ""

        if is_ok:
            st.success(f"Your answer: **{u}**")
        else:
            st.error(f"Your answer: **{u}**")
            st.info(f"Correct answer: **{c}**")

        st.markdown(f"**Explanation:** {q.get('explanation', '')}")


def render_attempt_review(attempt_id: int):
    attempt, questions = fetch_attempt_detail(attempt_id)

    if not attempt:
        st.error("Attempt not found.")
        if st.button("← Back to History"):
            open_history_view()
            st.rerun()
        return

    st.subheader("Attempt Review")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Student", attempt["student_name"])
    col2.metric("Score", f"{attempt['score']}/{attempt['total_questions']}")
    col3.metric("Accuracy", f"{attempt['accuracy']}%")
    col4.metric("Date", attempt["date_time"][:10])

    st.info(
        f"**Topic:** {attempt['topic']} · **Type:** {attempt['quiz_type']} · "
        f"**Mode:** {attempt['quiz_mode']}"
        + (f" · **Difficulty:** {attempt['difficulty']}" if attempt.get("difficulty") else "")
    )

    st.divider()
    st.markdown("### Questions")

    for i, q in enumerate(questions, start=1):
        _render_question_card(q, i)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back to History", use_container_width=True):
            open_history_view()
            st.rerun()
    with c2:
        if st.button("← Home", use_container_width=True):
            close_history_views()
            st.rerun()


def render_history_page():
    attempt_id = st.session_state.get("view_attempt_id")
    if attempt_id:
        render_attempt_review(attempt_id)
    else:
        render_history_list()
