from config import MAX_CONTENT_CHARS, MIN_PDF_CONTENT_CHARS, SOURCE_PDF, SOURCE_TOPIC


def normalize_content(text: str) -> str:
    return " ".join(text.split())


def truncate_content(text: str, max_chars: int = MAX_CONTENT_CHARS) -> tuple[str, bool]:
    """Return (possibly truncated text, was_truncated). Used for PDF content only."""
    text = text.strip()
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n\n[Content truncated due to length.]", True


def validate_quiz_topic(topic: str) -> str:
    """Short topic/subject/keyword — no minimum length beyond non-empty."""
    cleaned = normalize_content(topic)
    if not cleaned:
        raise ValueError("Please enter a quiz topic or subject name.")
    if len(cleaned) < 2:
        raise ValueError("Topic is too short. Enter at least 2 characters (e.g. Python, DBMS).")
    return cleaned


def validate_pdf_content(content: str) -> str:
    """Extracted PDF text must have enough material to generate questions."""
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("No readable text found in the PDF.")
    if len(cleaned) < MIN_PDF_CONTENT_CHARS:
        raise ValueError(
            f"The PDF has too little text (need at least {MIN_PDF_CONTENT_CHARS} characters). "
            "Try a different file with more content."
        )
    return cleaned


def validate_quiz_source(source: str) -> None:
    if source not in (SOURCE_TOPIC, SOURCE_PDF):
        raise ValueError(f"Unknown quiz source: {source}")
