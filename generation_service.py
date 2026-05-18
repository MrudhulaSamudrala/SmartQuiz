"""
Orchestrates quiz generation from topic text or PDF uploads.
"""

from config import SOURCE_PDF, SOURCE_TOPIC
from content_utils import truncate_content, validate_topic_content
from pdf_extractor import extract_text_from_pdf
from quiz_generation import generate_quiz


def prepare_content_from_request(params: dict) -> tuple[str, bool]:
    """
    Build normalized source content from pending generation params.
    Returns (content, was_truncated).
    """
    source = params["quiz_source"]

    if source == SOURCE_TOPIC:
        content = validate_topic_content(params["source_content"])
        return truncate_content(content)

    if source == SOURCE_PDF:
        pdf_bytes = params.get("pdf_bytes")
        if not pdf_bytes:
            raise ValueError("No PDF file was uploaded.")
        extracted = extract_text_from_pdf(pdf_bytes)
        content = validate_topic_content(extracted)
        return truncate_content(content)

    raise ValueError(f"Unsupported quiz source: {source}")


def run_quiz_generation(params: dict) -> list[dict]:
    content, _ = prepare_content_from_request(params)
    return generate_quiz(
        source=params["quiz_source"],
        content=content,
        difficulty=params["difficulty"],
        num_questions=params["num_questions"],
        quiz_type=params["quiz_type"],
    )
