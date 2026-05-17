import json
import os
import re
import time
from pathlib import Path

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DIFFICULTIES = ["Easy", "Medium", "Hard"]
OPTION_LABELS = ["A", "B", "C", "D"]
TIMER_OPTIONS = [5, 10, 15, 30, 60]
GEMINI_MODELS = [
    os.getenv("GEMINI_MODEL", "").strip(),
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]
GEMINI_MODELS = [m for m in GEMINI_MODELS if m]


# --- Gemini helpers ---


def get_api_key() -> str | None:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    return key or None


def configure_gemini() -> bool:
    api_key = get_api_key()
    if not api_key:
        return False
    genai.configure(api_key=api_key)
    return True


def friendly_api_error(exc: Exception) -> str:
    msg = str(exc)
    if "404" in msg or "not found" in msg.lower():
        return (
            "That AI model is not available on your API key. "
            "The app will try gemini-2.5-flash automatically — restart and generate again."
        )
    if "API_KEY_INVALID" in msg or ("invalid" in msg.lower() and "api" in msg.lower()):
        return "Invalid API key. Create a new key at https://aistudio.google.com/apikey and update .env"
    if "429" in msg or "quota" in msg.lower() or "RESOURCE_EXHAUSTED" in msg:
        return "API quota exceeded. Wait a minute and try again, or check usage at https://ai.dev/rate-limit"
    return msg


def extract_json(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def generate_quiz(topic: str, difficulty: str, num_questions: int) -> list[dict]:
    prompt = f"""You are an expert quiz creator for students.

Create exactly {num_questions} multiple-choice questions on the topic: "{topic}".
Difficulty level: {difficulty}.

Return ONLY a valid JSON array. No markdown, no extra text.
Each object must have this exact structure:
{{
  "question": "string",
  "options": ["option A", "option B", "option C", "option D"],
  "correct_index": 0,
  "explanation": "brief explanation of why the correct answer is right"
}}

Rules:
- correct_index is 0 for first option, 1 for second, 2 for third, 3 for fourth
- options must have exactly 4 items
- questions must match the {difficulty} difficulty
- explanations should be educational and concise
"""

    last_error = None
    response = None
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            break
        except Exception as exc:
            last_error = exc
            continue

    if response is None:
        raise RuntimeError(friendly_api_error(last_error or RuntimeError("No model available")))

    questions = extract_json(response.text)

    if not isinstance(questions, list) or len(questions) == 0:
        raise ValueError("AI returned an empty or invalid quiz.")

    for i, q in enumerate(questions):
        if not all(k in q for k in ("question", "options", "correct_index", "explanation")):
            raise ValueError(f"Question {i + 1} is missing required fields.")
        if len(q["options"]) != 4:
            raise ValueError(f"Question {i + 1} must have exactly 4 options.")
        if q["correct_index"] not in (0, 1, 2, 3):
            raise ValueError(f"Question {i + 1} has an invalid correct_index.")

    return questions[:num_questions]


# --- Session state helpers ---


def init_session():
    defaults = {
        "quiz": None,
        "answers": {},
        "submitted": False,
        "quiz_started": False,
        "current_question": 0,
        "time_per_question": 30,
        "question_started_at": 0.0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_quiz():
    st.session_state.quiz = None
    st.session_state.answers = {}
    st.session_state.submitted = False
    st.session_state.quiz_started = False
    st.session_state.current_question = 0
    st.session_state.question_started_at = 0.0


def start_timed_quiz():
    st.session_state.quiz_started = True
    st.session_state.current_question = 0
    st.session_state.answers = {}
    st.session_state.submitted = False
    st.session_state.question_started_at = time.time()


def seconds_remaining() -> int:
    elapsed = time.time() - st.session_state.question_started_at
    return max(0, st.session_state.time_per_question - int(elapsed))


def advance_question():
    """Move to the next question, or finish the quiz."""
    st.session_state.current_question += 1
    total = len(st.session_state.quiz)

    if st.session_state.current_question >= total:
        st.session_state.submitted = True
        st.session_state.quiz_started = False
    else:
        st.session_state.question_started_at = time.time()


def save_answer_and_advance(option_index: int):
    q_idx = st.session_state.current_question
    st.session_state.answers[q_idx] = option_index
    advance_question()


# --- UI screens ---


def render_setup():
    st.subheader("Create your quiz")
    topic = st.text_input("Topic", placeholder="e.g. Python loops, World War II, Photosynthesis")

    col1, col2 = st.columns(2)
    with col1:
        difficulty = st.selectbox("Difficulty", DIFFICULTIES)
    with col2:
        num_questions = st.number_input("Number of questions", min_value=1, max_value=15, value=5)

    st.subheader("Timer settings")
    timer_label = st.selectbox(
        "Seconds per question",
        TIMER_OPTIONS,
        format_func=lambda s: f"{s} seconds",
        index=3,
    )
    st.session_state.time_per_question = timer_label

    if st.button("Generate Quiz", type="primary", use_container_width=True):
        if not topic.strip():
            st.warning("Please enter a topic.")
            return
        if not configure_gemini():
            st.error("Set GEMINI_API_KEY in a .env file. See .env.example.")
            return

        with st.spinner("Generating questions with AI..."):
            try:
                st.session_state.quiz = generate_quiz(
                    topic.strip(), difficulty, int(num_questions)
                )
                st.session_state.answers = {}
                st.session_state.submitted = False
                st.session_state.quiz_started = False
                st.session_state.current_question = 0
                st.rerun()
            except json.JSONDecodeError:
                st.error("Could not parse AI response. Please try again.")
            except Exception as exc:
                st.error(f"Generation failed: {friendly_api_error(exc)}")


def render_quiz_ready():
    quiz = st.session_state.quiz
    secs = st.session_state.time_per_question

    st.success(f"Quiz ready — {len(quiz)} questions")
    st.info(f"Each question has **{secs} seconds**. Unanswered questions count as wrong.")

    if st.button("Start Timed Quiz", type="primary", use_container_width=True):
        start_timed_quiz()
        st.rerun()

    if st.button("New quiz"):
        reset_quiz()
        st.rerun()


@st.fragment(run_every=1)
def countdown_timer():
    """Redraws every second so the countdown visibly ticks down."""
    if not st.session_state.quiz_started:
        return

    remaining = seconds_remaining()
    secs = st.session_state.time_per_question

    # Timer UI must be inside this fragment (refreshes every 1 second)
    st.markdown("#### ⏱ Time remaining")
    st.metric(label="Seconds left", value=remaining, delta=f"-{secs - remaining}s" if remaining < secs else None, delta_color="off")

    st.progress(
        remaining / secs if secs else 0,
        text=f"{remaining} / {secs} seconds",
    )

    if remaining <= 0:
        advance_question()
        st.rerun()


def render_timed_quiz():
    quiz = st.session_state.quiz
    total = len(quiz)
    q_idx = st.session_state.current_question
    q = quiz[q_idx]

    if st.button("Quit quiz"):
        reset_quiz()
        st.rerun()

    st.divider()

    st.progress((q_idx + 1) / total, text=f"Question {q_idx + 1} of {total}")
    st.markdown(f"### Question {q_idx + 1} of {total}")

    countdown_timer()

    st.markdown(f"**{q['question']}**")

    choice = st.radio(
        "Choose an answer",
        q["options"],
        key=f"timed_q_{q_idx}",
        index=None,
        label_visibility="collapsed",
    )

    if choice is not None:
        save_answer_and_advance(q["options"].index(choice))
        st.rerun()


def render_results():
    quiz = st.session_state.quiz
    score = sum(
        1
        for i, q in enumerate(quiz)
        if st.session_state.answers.get(i) == q["correct_index"]
    )
    total = len(quiz)
    skipped = sum(1 for i in range(total) if i not in st.session_state.answers)
    pct = round(100 * score / total) if total else 0

    st.subheader("Your results")
    st.metric("Score", f"{score} / {total} ({pct}%)")
    if skipped:
        st.caption(f"{skipped} question(s) skipped or timed out (counted as wrong)")

    if pct >= 80:
        st.balloons()
        st.success("Great job!")
    elif pct >= 50:
        st.info("Good effort — review the explanations below.")
    else:
        st.warning("Keep practicing — read the explanations to learn more.")

    st.divider()

    for i, q in enumerate(quiz):
        user_idx = st.session_state.answers.get(i)
        correct_idx = q["correct_index"]
        is_correct = user_idx is not None and user_idx == correct_idx

        st.markdown(f"**Q{i + 1}. {q['question']}**")
        for j, opt in enumerate(q["options"]):
            prefix = OPTION_LABELS[j]
            if j == correct_idx:
                st.markdown(f"- :green[{prefix}. {opt}] (correct)")
            elif user_idx is not None and j == user_idx:
                st.markdown(f"- :red[{prefix}. {opt}] (your answer)")
            else:
                st.markdown(f"- {prefix}. {opt}")

        if user_idx is None:
            st.error("Skipped — time ran out or no answer given")
        elif is_correct:
            st.success("Correct")
        else:
            st.error(
                f"Incorrect — you chose {OPTION_LABELS[user_idx]}, "
                f"correct answer is {OPTION_LABELS[correct_idx]}"
            )
        st.info(f"Explanation: {q['explanation']}")
        st.divider()

    if st.button("Start a new quiz", use_container_width=True):
        reset_quiz()
        st.rerun()


def main():
    st.set_page_config(page_title="AI Quiz Generator", page_icon="📝", layout="centered")
    init_session()

    st.title("AI Quiz Generator")
    st.caption("Powered by Google Gemini · Built with Streamlit")

    with st.sidebar:
        st.subheader("API status")
        key = get_api_key()
        if key:
            st.success("Gemini API key loaded")
            st.caption(f"Using model: {GEMINI_MODELS[0]}")
        else:
            st.error("No API key found")
            st.markdown(
                "1. Copy `.env.example` to `.env`\n"
                "2. Add your key from [Google AI Studio](https://aistudio.google.com/apikey)\n"
                "3. Restart the app"
            )

        if st.session_state.quiz_started:
            st.divider()
            st.caption("Timed quiz in progress")
            st.caption(f"{st.session_state.time_per_question}s per question")

    if st.session_state.submitted and st.session_state.quiz:
        render_results()
    elif st.session_state.quiz_started:
        render_timed_quiz()
    elif st.session_state.quiz:
        render_quiz_ready()
    else:
        render_setup()


if __name__ == "__main__":
    main()
