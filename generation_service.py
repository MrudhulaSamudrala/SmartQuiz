"""
Orchestrates quiz generation from topic keywords or PDF uploads.
"""

from config import SOURCE_PDF, SOURCE_TOPIC
from content_utils import truncate_content, validate_pdf_content, validate_quiz_topic
from pdf_extractor import extract_text_from_pdf
from quiz_generation import generate_quiz


def prepare_content_from_request(params: dict) -> tuple[str, bool]:
    """
    Build content for the AI prompt.
    Topic mode: short keyword (no truncation).
    PDF mode: extracted text (validated + truncated if needed).
    """
    source = params["quiz_source"]

    if source == SOURCE_TOPIC:
        topic = validate_quiz_topic(params["source_content"])
        return topic, False

    if source == SOURCE_PDF:
        pdf_bytes = params.get("pdf_bytes")
        if not pdf_bytes:
            raise ValueError("No PDF file was uploaded.")
        extracted = extract_text_from_pdf(pdf_bytes)
        content = validate_pdf_content(extracted)
        return truncate_content(content)

    raise ValueError(f"Unsupported quiz source: {source}")


def run_quiz_generation(params: dict) -> list[dict]:
    content, was_truncated = prepare_content_from_request(params)
    return generate_quiz(
        source=params["quiz_source"],
        content=content,
        difficulty=params["difficulty"],
        num_questions=params["num_questions"],
        quiz_type=params["quiz_type"],
        content_truncated=was_truncated,
    )
