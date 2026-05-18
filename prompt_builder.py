from config import (
    QUIZ_TYPE_MCQ,
    QUIZ_TYPE_MIXED,
    QUIZ_TYPE_ONE_WORD,
    QUIZ_TYPE_TF,
    SOURCE_PDF,
    SOURCE_TOPIC,
)


def _type_schema(quiz_type: str, num_questions: int) -> str:
    if quiz_type == QUIZ_TYPE_MCQ:
        return f"""Create exactly {num_questions} multiple-choice questions.
Each object:
{{
  "type": "mcq",
  "question": "string",
  "options": ["A", "B", "C", "D"],
  "correct_index": 0,
  "explanation": "string"
}}
Rules: correct_index 0-3, exactly 4 options."""

    if quiz_type == QUIZ_TYPE_TF:
        return f"""Create exactly {num_questions} true/false questions.
Each object:
{{
  "type": "true_false",
  "question": "statement to judge as true or false",
  "correct_answer": true,
  "explanation": "string"
}}
Rules: correct_answer must be boolean true or false."""

    if quiz_type == QUIZ_TYPE_ONE_WORD:
        return f"""Create exactly {num_questions} one-word-answer questions.
Each object:
{{
  "type": "one_word",
  "question": "string",
  "correct_answer": "singleword",
  "explanation": "string"
}}
Rules: correct_answer must be ONE word only (no spaces)."""

    return f"""Create exactly {num_questions} questions mixing mcq, true_false, and one_word randomly.
Each object must include a "type" field.

MCQ: {{"type":"mcq","question":"...","options":["...","...","...","..."],"correct_index":0,"explanation":"..."}}
True/False: {{"type":"true_false","question":"...","correct_answer":true,"explanation":"..."}}
One-word: {{"type":"one_word","question":"...","correct_answer":"word","explanation":"..."}}"""


def build_topic_prompt(
    topic: str,
    difficulty: str,
    num_questions: int,
    quiz_type: str,
) -> str:
    """
    Keyword/topic-based generation.
    Example: Generate a Medium difficulty MCQ quiz on Python Loops.
    """
    return f"""You are an expert quiz creator for students.

Generate a {difficulty} difficulty {quiz_type} quiz on the topic: "{topic}".

Use your knowledge of this subject to create accurate, educational questions.
Questions should be appropriate for the {difficulty} level.
Cover key concepts a student should know about "{topic}".

{_type_schema(quiz_type, num_questions)}

Return ONLY a valid JSON array. No markdown, no extra commentary.
Explanations should be educational and concise.
"""


def build_pdf_prompt(
    content: str,
    difficulty: str,
    num_questions: int,
    quiz_type: str,
    content_truncated: bool = False,
) -> str:
    """PDF mode: questions must come only from extracted document text."""
    truncation_note = (
        "\nNote: The PDF content was truncated to fit length limits. "
        "Focus questions on the material provided."
        if content_truncated
        else ""
    )

    return f"""You are an expert quiz creator for students.

Generate a {difficulty} difficulty {quiz_type} quiz using ONLY the PDF content below.
Do not use outside knowledge. Every question must be answerable from the text.
{truncation_note}

--- PDF CONTENT START ---
{content}
--- PDF CONTENT END ---

{_type_schema(quiz_type, num_questions)}

Return ONLY a valid JSON array. No markdown, no extra commentary.
Explanations should be educational and concise.
"""


def build_quiz_prompt(
    source: str,
    content: str,
    difficulty: str,
    num_questions: int,
    quiz_type: str,
    content_truncated: bool = False,
) -> str:
    if source == SOURCE_TOPIC:
        return build_topic_prompt(content, difficulty, num_questions, quiz_type)
    if source == SOURCE_PDF:
        return build_pdf_prompt(
            content, difficulty, num_questions, quiz_type, content_truncated
        )
    return build_topic_prompt(content, difficulty, num_questions, quiz_type)
