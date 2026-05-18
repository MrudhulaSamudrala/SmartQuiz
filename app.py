import json

import streamlit as st

from config import (
    DIFFICULTIES,
    GEMINI_MODELS,
    MODE_TIMED,
    QUIZ_MODES,
    QUIZ_SOURCES,
    QUIZ_TYPES,
    SOURCE_PDF,
    SOURCE_TOPIC,
    TIMER_OPTIONS,
)
from gemini_client import configure_gemini, friendly_api_error, get_api_key
from generation_service import run_quiz_generation
from history_service import ensure_database, save_attempt_from_session
from quiz_ui import render_quiz_screen, render_results_review, render_score_summary
from review_ui import open_history_view, render_history_page
from session_state import (
    apply_generated_quiz,
    get_student_name,
    has_student_name,
    init_session,
    is_timed_mode,
    request_quiz_generation,
    reset_quiz,
    resolve_page,
    start_quiz,
)


def execute_pending_generation():
    pending = st.session_state.pending_generation
    if not pending:
        return

    if pending.get("student_name"):
        st.session_state.student_name_saved = pending["student_name"]

    st.session_state.pending_generation = None
    st.session_state.loading = True

    try:
        if not configure_gemini():
            st.session_state.generation_error = "Set GEMINI_API_KEY in a .env file. See .env.example."
            return

        source = pending["quiz_source"]
        if source == SOURCE_PDF:
            spinner_msg = "Extracting PDF text and generating questions with AI..."
        else:
            spinner_msg = "Generating quiz from your topic..."

        with st.spinner(spinner_msg):
            quiz = run_quiz_generation(pending)

        if pending.get("student_name"):
            st.session_state.student_name_saved = pending["student_name"]

        apply_generated_quiz(
            quiz,
            pending["quiz_type"],
            pending["quiz_mode"],
            pending["timer_secs"],
            pending["quiz_source"],
            pending.get("source_label", ""),
            pending.get("difficulty", ""),
        )
        st.session_state.generation_error = None

    except json.JSONDecodeError:
        st.session_state.generation_error = "Could not parse AI response. Please try again."
    except Exception as exc:
        st.session_state.generation_error = str(exc) if str(exc) else friendly_api_error(exc)
    finally:
        st.session_state.loading = False

    st.rerun()


def _render_source_inputs(quiz_source: str):
    """Show topic input or PDF uploader based on quiz source."""
    if quiz_source == SOURCE_TOPIC:
        st.markdown("Enter a **subject**, **topic**, or **keyword** — no long text needed.")
        return st.text_input(
            "Enter Quiz Topic",
            placeholder="e.g. Python, DBMS, Machine Learning, Java Loops, Operating Systems",
            label_visibility="visible",
        ), None

    st.markdown("Upload a **PDF** file. Questions will be generated only from its content.")
    uploaded = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        help="Text-based PDFs work best. Scanned image-only PDFs may fail.",
    )
    return None, uploaded


def _build_generation_params(
    quiz_source: str,
    source_text: str | None,
    uploaded_pdf,
    difficulty: str,
    num_questions: int,
    quiz_type: str,
    quiz_mode: str,
    timer_secs: int,
) -> dict | None:
    params = {
        "quiz_source": quiz_source,
        "difficulty": difficulty,
        "num_questions": int(num_questions),
        "quiz_type": quiz_type,
        "quiz_mode": quiz_mode,
        "timer_secs": timer_secs if quiz_mode == MODE_TIMED else 0,
    }

    if quiz_source == SOURCE_TOPIC:
        if not source_text or not source_text.strip():
            st.warning("Please enter a quiz topic or subject name.")
            return None
        params["source_content"] = source_text.strip()
        preview = source_text.strip()[:60]
        params["source_label"] = preview + ("..." if len(source_text.strip()) > 60 else "")
        return params

    if uploaded_pdf is None:
        st.warning("Please upload a PDF file.")
        return None

    if uploaded_pdf.type and uploaded_pdf.type != "application/pdf":
        st.error("Only PDF files are allowed.")
        return None

    pdf_bytes = uploaded_pdf.read()
    if not pdf_bytes:
        st.error("The uploaded file is empty.")
        return None

    params["pdf_bytes"] = pdf_bytes
    params["source_label"] = uploaded_pdf.name
    return params


def render_setup():
    st.subheader("Create your quiz")

    if st.session_state.generation_error:
        st.error(st.session_state.generation_error)

    quiz_source = st.selectbox("Quiz Source", QUIZ_SOURCES)
    source_text, uploaded_pdf = _render_source_inputs(quiz_source)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        difficulty = st.selectbox("Difficulty", DIFFICULTIES)
    with col2:
        num_questions = st.number_input("Number of questions", min_value=1, max_value=15, value=5)

    quiz_type = st.selectbox("Quiz Type", QUIZ_TYPES)
    quiz_mode = st.selectbox("Quiz Mode", QUIZ_MODES)

    timer_secs = 30
    if quiz_mode == MODE_TIMED:
        st.subheader("Timer settings")
        timer_secs = st.selectbox(
            "Seconds per question",
            TIMER_OPTIONS,
            format_func=lambda s: f"{s} seconds",
            index=3,
        )

    if st.button("Generate Quiz", type="primary", use_container_width=True):
        if not has_student_name():
            st.warning("Enter your name in the sidebar once, then generate your quiz.")
            return
        params = _build_generation_params(
            quiz_source,
            source_text,
            uploaded_pdf,
            difficulty,
            num_questions,
            quiz_type,
            quiz_mode,
            timer_secs,
        )
        if params:
            request_quiz_generation(params)


def render_loading():
    st.subheader("Generating your quiz...")
    with st.spinner("Please wait — this may take a moment..."):
        st.empty()


def render_quiz_ready():
    quiz = st.session_state.quiz_data
    qtype = st.session_state.quiz_type or "Quiz"
    mode = st.session_state.quiz_mode
    source = st.session_state.quiz_source or "Unknown"
    label = st.session_state.source_label or ""

    st.success(f"Quiz ready — {len(quiz)} questions")
    st.caption(f"Source: **{source}**" + (f" · `{label}`" if label else ""))

    if is_timed_mode():
        secs = st.session_state.time_per_question
        st.info(f"**{mode}** · **{qtype}** · **{secs}s** per question · Unanswered = wrong")
    else:
        st.info(f"**{mode}** · **{qtype}** · Take as long as you need · Unanswered = wrong")

    if has_student_name():
        st.caption(f"Playing as **{get_student_name()}**")

    if st.button("Start Quiz", type="primary", use_container_width=True):
        start_quiz()

    if st.button("New quiz"):
        reset_quiz()
        st.rerun()


def render_playing_quiz():
    render_quiz_screen()
    if st.session_state.quiz_completed:
        render_results()


def render_results():
    quiz = st.session_state.quiz_data
    answers = st.session_state.answers

    st.caption(f"Mode: {st.session_state.quiz_mode} · Source: {st.session_state.quiz_source}")

    attempt_id = save_attempt_from_session()
    if attempt_id:
        st.success(f"Quiz saved to history (attempt #{attempt_id}).")

    render_score_summary(quiz, answers)
    st.divider()
    render_results_review(quiz, answers)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("View Quiz History", use_container_width=True):
            open_history_view()
            st.rerun()
    with col2:
        if st.button("Start a new quiz", use_container_width=True):
            reset_quiz()
            st.rerun()


def _on_student_name_change():
    """Backup name when user types (safe — does not write to widget key)."""
    from session_state import persist_student_name_backup

    persist_student_name_backup()


def _render_sidebar_student_name():
    """Single name input for the whole app. Widget owns key 'student_name'."""
    if "student_name" not in st.session_state:
        st.session_state.student_name = ""

    st.text_input(
        "Student name",
        key="student_name",
        placeholder="Enter your name once",
        help="Enter once — used for the whole session and quiz history",
        on_change=_on_student_name_change,
    )


def main():
    st.set_page_config(page_title="AI Quiz Generator", page_icon="📝", layout="centered")
    init_session()

    # Student name widget FIRST so it exists before generation reruns
    with st.sidebar:
        st.subheader("Student")
        _render_sidebar_student_name()
        if has_student_name():
            st.caption(f"Welcome, {get_student_name()}!")

    ensure_database()
    execute_pending_generation()

    st.title("AI Quiz Generator")
    st.caption("Powered by Google Gemini · Built with Streamlit")

    with st.sidebar:
        st.divider()
        st.subheader("API status")
        key = get_api_key()
        if key:
            st.success("Gemini API key loaded")
            st.caption(f"Model: {GEMINI_MODELS[0]}")
        else:
            st.error("No API key found")
            st.markdown(
                "1. Copy `.env.example` to `.env`\n"
                "2. Add your key from [Google AI Studio](https://aistudio.google.com/apikey)\n"
                "3. Restart the app"
            )

        if st.session_state.quiz_type:
            st.divider()
            st.caption(f"Quiz type: {st.session_state.quiz_type}")

        if st.session_state.quiz_generated:
            st.caption(f"Quiz mode: {st.session_state.quiz_mode}")
            if st.session_state.quiz_source:
                st.caption(f"Source: {st.session_state.quiz_source}")

        if st.session_state.quiz_started and is_timed_mode():
            st.caption(f"Timer: {st.session_state.time_per_question}s per question")

        st.divider()
        if st.button("Quiz History", use_container_width=True):
            open_history_view()
            st.rerun()

    page = resolve_page()

    if page == "loading":
        render_loading()
    elif page == "history":
        render_history_page()
    elif page == "results":
        render_results()
    elif page == "playing":
        render_playing_quiz()
    elif page == "ready":
        render_quiz_ready()
    else:
        render_setup()


if __name__ == "__main__":
    main()
