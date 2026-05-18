from config import (
    QUIZ_TYPE_MCQ,
    QUIZ_TYPE_MIXED,
    QUIZ_TYPE_ONE_WORD,
    QUIZ_TYPE_TF,
    TYPE_MCQ,
    TYPE_ONE_WORD,
    TYPE_TRUE_FALSE,
)
from content_utils import validate_quiz_source
from gemini_client import extract_json, generate_content
from prompt_builder import build_quiz_prompt


def validate_question(q: dict, index: int) -> None:
    n = index + 1
    qtype = q.get("type")

    if "question" not in q or "explanation" not in q:
        raise ValueError(f"Question {n} is missing question or explanation.")

    if qtype == TYPE_MCQ:
        if len(q.get("options", [])) != 4:
            raise ValueError(f"Question {n} (MCQ) must have 4 options.")
        if q.get("correct_index") not in (0, 1, 2, 3):
            raise ValueError(f"Question {n} (MCQ) has invalid correct_index.")
    elif qtype == TYPE_TRUE_FALSE:
        if not isinstance(q.get("correct_answer"), bool):
            raise ValueError(f"Question {n} (True/False) needs boolean correct_answer.")
    elif qtype == TYPE_ONE_WORD:
        ans = str(q.get("correct_answer", "")).strip()
        if not ans or " " in ans:
            raise ValueError(f"Question {n} (One Word) needs a single-word correct_answer.")
        q["correct_answer"] = ans
    else:
        raise ValueError(f"Question {n} has unknown type: {qtype}")


def generate_quiz(
    source: str,
    content: str,
    difficulty: str,
    num_questions: int,
    quiz_type: str,
    content_truncated: bool = False,
) -> list[dict]:
    """
    Generate a quiz from a topic keyword or PDF-extracted text.
    Content preparation (validation/truncation) happens in generation_service.
    """
    validate_quiz_source(source)

    prompt = build_quiz_prompt(
        source=source,
        content=content,
        difficulty=difficulty,
        num_questions=num_questions,
        quiz_type=quiz_type,
        content_truncated=content_truncated,
    )

    raw = generate_content(prompt)
    questions = extract_json(raw)

    if not isinstance(questions, list) or len(questions) == 0:
        raise ValueError("AI returned an empty or invalid quiz.")

    for i, q in enumerate(questions):
        validate_question(q, i)

    return questions[:num_questions]


# Backward-compatible alias
def generate_quiz_from_topic(
    topic: str, difficulty: str, num_questions: int, quiz_type: str
) -> list[dict]:
    from config import SOURCE_TOPIC

    return generate_quiz(SOURCE_TOPIC, topic, difficulty, num_questions, quiz_type)
