import time
from typing import Any

import streamlit as st

from config import MODE_TIMED, TYPE_MCQ, TYPE_ONE_WORD, TYPE_TRUE_FALSE


def init_session():
    defaults = {
        "quiz_data": None,
        "quiz_type": None,
        "quiz_source": None,
        "source_label": None,
        "quiz_mode": MODE_TIMED,
        "quiz_generated": False,
        "quiz_started": False,
        "quiz_completed": False,
        "submitted": False,
        "answers": {},
        "selected_answer": {},
        "current_question": 0,
        "time_per_question": 30,
        "timer_start": 0.0,
        "timer_question_idx": -1,
        "remaining_time": 0,
        "loading": False,
        "pending_generation": None,
        "generation_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def is_timed_mode() -> bool:
    return st.session_state.get("quiz_mode") == MODE_TIMED


def get_quiz() -> list[dict] | None:
    return st.session_state.quiz_data


def reset_quiz():
    st.session_state.quiz_data = None
    st.session_state.quiz_type = None
    st.session_state.quiz_source = None
    st.session_state.source_label = None
    st.session_state.quiz_mode = MODE_TIMED
    st.session_state.quiz_generated = False
    st.session_state.quiz_started = False
    st.session_state.quiz_completed = False
    st.session_state.submitted = False
    st.session_state.answers = {}
    st.session_state.selected_answer = {}
    st.session_state.current_question = 0
    st.session_state.timer_start = 0.0
    st.session_state.timer_question_idx = -1
    st.session_state.remaining_time = 0
    st.session_state.loading = False
    st.session_state.pending_generation = None
    st.session_state.generation_error = None


def request_quiz_generation(params: dict[str, Any]):
    if st.session_state.loading or st.session_state.pending_generation:
        return
    st.session_state.generation_error = None
    st.session_state.pending_generation = params
    st.rerun()


def apply_generated_quiz(
    quiz: list[dict],
    quiz_type: str,
    quiz_mode: str,
    timer_secs: int,
    quiz_source: str,
    source_label: str = "",
):
    st.session_state.quiz_data = quiz
    st.session_state.quiz_type = quiz_type
    st.session_state.quiz_source = quiz_source
    st.session_state.source_label = source_label
    st.session_state.quiz_mode = quiz_mode
    st.session_state.time_per_question = timer_secs
    st.session_state.quiz_generated = True
    st.session_state.quiz_started = False
    st.session_state.quiz_completed = False
    st.session_state.submitted = False
    st.session_state.answers = {}
    st.session_state.selected_answer = {}
    st.session_state.current_question = 0
    st.session_state.timer_question_idx = -1


def resolve_page() -> str:
    if st.session_state.loading:
        return "loading"
    if st.session_state.submitted or st.session_state.quiz_completed:
        return "results"
    if st.session_state.quiz_started:
        return "playing"
    if st.session_state.quiz_generated and st.session_state.quiz_data:
        return "ready"
    return "setup"


def start_quiz():
    st.session_state.quiz_started = True
    st.session_state.quiz_completed = False
    st.session_state.submitted = False
    st.session_state.current_question = 0
    st.session_state.answers = {}
    st.session_state.selected_answer = {}
    if is_timed_mode():
        _start_timer_for_question(0)
    st.rerun()


def finish_quiz():
    st.session_state.quiz_completed = True
    st.session_state.submitted = True
    st.session_state.quiz_started = False


def _start_timer_for_question(q_idx: int):
    st.session_state.timer_question_idx = q_idx
    st.session_state.timer_start = time.time()
    st.session_state.remaining_time = st.session_state.time_per_question


def sync_question_timer():
    if not is_timed_mode():
        return
    q_idx = st.session_state.current_question
    if st.session_state.timer_question_idx != q_idx:
        _start_timer_for_question(q_idx)


def seconds_remaining() -> int:
    elapsed = time.time() - st.session_state.timer_start
    remaining = max(0, st.session_state.time_per_question - int(elapsed))
    st.session_state.remaining_time = remaining
    return remaining


def get_widget_selection(question: dict, q_idx: int) -> Any | None:
    qtype = question["type"]

    if qtype == TYPE_MCQ:
        choice = st.session_state.get(f"mcq_{q_idx}")
        if choice is None:
            return None
        return question["options"].index(choice)

    if qtype == TYPE_TRUE_FALSE:
        choice = st.session_state.get(f"tf_{q_idx}")
        if choice is None:
            return None
        return choice == "True"

    if qtype == TYPE_ONE_WORD:
        value = st.session_state.get(f"ow_{q_idx}", "").strip()
        return value if value else None

    return None


def sync_selected_answer(question: dict, q_idx: int):
    selection = get_widget_selection(question, q_idx)
    if selection is not None:
        st.session_state.selected_answer[q_idx] = selection
    elif q_idx in st.session_state.selected_answer:
        del st.session_state.selected_answer[q_idx]


def has_current_selection(question: dict, q_idx: int) -> bool:
    return get_widget_selection(question, q_idx) is not None


def commit_answer_and_advance(question: dict):
    if not st.session_state.quiz_started:
        return

    idx = st.session_state.current_question
    selection = get_widget_selection(question, idx)

    if selection is not None:
        st.session_state.answers[idx] = selection

    st.session_state.selected_answer.pop(idx, None)
    advance_to_next_question()


def advance_to_next_question():
    st.session_state.current_question += 1
    total = len(st.session_state.quiz_data)

    if st.session_state.current_question >= total:
        finish_quiz()
    elif is_timed_mode():
        _start_timer_for_question(st.session_state.current_question)


def process_question_timeout(question: dict):
    """Timed mode only: auto-advance when countdown reaches zero."""
    if not st.session_state.quiz_started or not is_timed_mode():
        return

    idx = st.session_state.current_question
    if seconds_remaining() > 0:
        return

    selection = get_widget_selection(question, idx)
    if selection is not None:
        st.session_state.answers[idx] = selection

    st.session_state.selected_answer.pop(idx, None)
    advance_to_next_question()
