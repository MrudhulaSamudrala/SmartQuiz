import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config import MODE_TIMED, MODE_UNTIMED, OPTION_LABELS, TYPE_LABELS, TYPE_MCQ, TYPE_ONE_WORD, TYPE_TRUE_FALSE
from quiz_scoring import calculate_score, format_correct_answer, format_user_answer, is_correct
from session_state import (
    commit_answer_and_advance,
    get_widget_selection,
    has_current_selection,
    is_timed_mode,
    process_question_timeout,
    seconds_remaining,
    sync_question_timer,
    sync_selected_answer,
)


# --- Shared UI components ---


def _render_mode_badge():
    mode = st.session_state.quiz_mode
    if mode == MODE_TIMED:
        st.caption(f"Mode: **{mode}** · {st.session_state.time_per_question}s per question")
    else:
        st.caption(f"Mode: **{mode}** · no time limit")


def _type_badge(q: dict):
    label = TYPE_LABELS.get(q["type"], q["type"])
    st.caption(f"Question type: **{label}**")


def render_timer_display():
    remaining = st.session_state.remaining_time
    secs = st.session_state.time_per_question

    st.markdown("#### ⏱ Time remaining")
    if remaining <= 5:
        st.error(f"**{remaining}** seconds left — hurry!")
    else:
        st.info(f"**{remaining}** seconds left")

    st.progress(
        remaining / secs if secs else 0,
        text=f"{remaining} / {secs} seconds",
    )


def _render_selection_hint(q: dict, q_idx: int, timed: bool):
    selection = get_widget_selection(q, q_idx)
    if selection is None:
        if timed:
            st.caption("Select an answer, then click **Next Question** (or wait for the timer).")
        else:
            st.caption("Select an answer, then click **Next Question** when you are ready.")
        return

    sync_selected_answer(q, q_idx)
    if timed:
        st.success(
            f"Selected: **{format_user_answer(q, selection)}** — you can change it before time runs out."
        )
    else:
        st.success(f"Selected: **{format_user_answer(q, selection)}** — you can change it anytime.")


def _render_mcq_input(q: dict, q_idx: int):
    st.radio(
        "Choose an answer",
        q["options"],
        key=f"mcq_{q_idx}",
        index=None,
        label_visibility="collapsed",
    )


def _render_true_false_input(q: dict, q_idx: int):
    st.radio(
        "True or False",
        ["True", "False"],
        key=f"tf_{q_idx}",
        index=None,
        horizontal=True,
        label_visibility="collapsed",
    )


def _render_one_word_input(q: dict, q_idx: int, timed: bool):
    if timed:
        st.caption("Type your answer below. You can edit it until the timer ends.")
    else:
        st.caption("Type your answer below. Take your time.")
    st.text_input(
        "Your answer",
        key=f"ow_{q_idx}",
        placeholder="One word answer",
        label_visibility="collapsed",
    )


def render_question_input(q: dict, q_idx: int, timed: bool):
    qtype = q["type"]
    if qtype == TYPE_MCQ:
        _render_mcq_input(q, q_idx)
    elif qtype == TYPE_TRUE_FALSE:
        _render_true_false_input(q, q_idx)
    elif qtype == TYPE_ONE_WORD:
        _render_one_word_input(q, q_idx, timed)

    _render_selection_hint(q, q_idx, timed)


def _render_quiz_header(q_idx: int, total: int, q: dict, timed: bool):
    st.progress((q_idx + 1) / total, text=f"Question {q_idx + 1} of {total}")
    st.markdown(f"### Question {q_idx + 1} of {total}")
    _render_mode_badge()
    _type_badge(q)
    if timed:
        render_timer_display()


def _render_next_button(q: dict, q_idx: int):
    has_selection = has_current_selection(q, q_idx)
    if st.button(
        "Next Question →",
        type="primary",
        use_container_width=True,
        disabled=not has_selection,
        help="Select an answer first" if not has_selection else "Save your answer and continue",
    ):
        commit_answer_and_advance(q)


def _render_quit_button():
    if st.button("Quit quiz"):
        from session_state import reset_quiz

        reset_quiz()
        st.rerun()


# --- Timed mode ---


def render_timed_quiz_screen():
    if not st.session_state.quiz_started:
        return

    quiz = st.session_state.quiz_data
    sync_question_timer()
    seconds_remaining()

    process_question_timeout(quiz[st.session_state.current_question])

    if st.session_state.quiz_completed:
        return

    q_idx = st.session_state.current_question
    q = quiz[q_idx]
    total = len(quiz)

    st_autorefresh(interval=1000, key=f"quiz_tick_{q_idx}")

    _render_quit_button()
    st.divider()

    _render_quiz_header(q_idx, total, q, timed=True)
    st.markdown(f"**{q['question']}**")
    render_question_input(q, q_idx, timed=True)
    _render_next_button(q, q_idx)


# --- Untimed mode ---


def render_untimed_quiz_screen():
    if not st.session_state.quiz_started:
        return

    quiz = st.session_state.quiz_data
    q_idx = st.session_state.current_question
    q = quiz[q_idx]
    total = len(quiz)

    _render_quit_button()
    st.divider()

    _render_quiz_header(q_idx, total, q, timed=False)
    st.markdown(f"**{q['question']}**")
    render_question_input(q, q_idx, timed=False)
    _render_next_button(q, q_idx)


# --- Dispatcher ---


def render_quiz_screen():
    """Route to timed or untimed quiz UI based on session_state.quiz_mode."""
    if is_timed_mode():
        render_timed_quiz_screen()
    else:
        render_untimed_quiz_screen()


# --- Results ---


def _render_mcq_review(q: dict, user_answer):
    correct_idx = q["correct_index"]
    for j, opt in enumerate(q["options"]):
        prefix = OPTION_LABELS[j]
        if j == correct_idx:
            st.markdown(f"- :green[{prefix}. {opt}] (correct)")
        elif user_answer is not None and j == user_answer:
            st.markdown(f"- :red[{prefix}. {opt}] (your answer)")
        else:
            st.markdown(f"- {prefix}. {opt}")


def render_results_review(quiz: list[dict], answers: dict):
    for i, q in enumerate(quiz):
        user_answer = answers.get(i)
        correct = is_correct(q, user_answer)

        st.markdown(f"**Q{i + 1}. [{TYPE_LABELS.get(q['type'], '')}] {q['question']}**")

        if q["type"] == TYPE_MCQ:
            _render_mcq_review(q, user_answer)
        else:
            st.markdown(f"- Your answer: **{format_user_answer(q, user_answer)}**")
            st.markdown(f"- Correct answer: **{format_correct_answer(q)}**")

        if user_answer is None:
            st.error("Skipped — no answer given")
        elif correct:
            st.success("Correct")
        else:
            st.error("Incorrect")
        st.info(f"Explanation: {q['explanation']}")
        st.divider()


def render_score_summary(quiz: list[dict], answers: dict):
    score, total, skipped = calculate_score(quiz, answers)
    pct = round(100 * score / total) if total else 0

    st.subheader("Your results")
    st.metric("Score", f"{score} / {total} ({pct}%)")
    if skipped:
        st.caption(f"{skipped} question(s) skipped (counted as wrong)")

    if pct >= 80:
        st.balloons()
        st.success("Great job!")
    elif pct >= 50:
        st.info("Good effort — review the explanations below.")
    else:
        st.warning("Keep practicing — read the explanations to learn more.")

    return score, total, pct
