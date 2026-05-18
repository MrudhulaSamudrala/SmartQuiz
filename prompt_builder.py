from config import (
    QUIZ_TYPE_MCQ,
    QUIZ_TYPE_MIXED,
    QUIZ_TYPE_ONE_WORD,
    QUIZ_TYPE_TF,
    SOURCE_PDF,
    SOURCE_TOPIC,
)


def _source_instructions(source: str) -> str:
    if source == SOURCE_TOPIC:
        return """SOURCE: Topic / study text provided by the user.
Generate questions ONLY from the study material below.
Do not add facts that are not supported by the material."""

    if source == SOURCE_PDF:
        return """SOURCE: Text extracted from an uploaded PDF document.
Generate questions ONLY from the PDF content below.
Do not use outside knowledge. Every question must be answerable from the text."""

    return "Generate questions from the provided content."


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


def build_quiz_prompt(
    source: str,
    content: str,
    difficulty: str,
    num_questions: int,
    quiz_type: str,
    content_truncated: bool = False,
) -> str:
    truncation_note = (
        "\nNote: The source content was truncated to fit length limits. "
        "Focus questions on the material provided."
        if content_truncated
        else ""
    )

    return f"""You are an expert quiz creator for students.

{_source_instructions(source)}

Difficulty: {difficulty}
Number of questions: exactly {num_questions}
Quiz type: {quiz_type}
{truncation_note}

--- STUDY MATERIAL START ---
{content}
--- STUDY MATERIAL END ---

{_type_schema(quiz_type, num_questions)}

Return ONLY a valid JSON array. No markdown, no extra commentary.
Explanations should be educational and concise.
Questions must match the {difficulty} difficulty level.
"""
