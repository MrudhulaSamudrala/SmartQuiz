from config import MAX_CONTENT_CHARS, MIN_CONTENT_CHARS, SOURCE_PDF, SOURCE_TOPIC


def normalize_content(text: str) -> str:
    return " ".join(text.split())


def truncate_content(text: str, max_chars: int = MAX_CONTENT_CHARS) -> tuple[str, bool]:
    """Return (possibly truncated text, was_truncated)."""
    text = text.strip()
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n\n[Content truncated due to length.]", True


def validate_topic_content(content: str) -> str:
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("Please enter a topic or paste study notes.")
    if len(cleaned) < MIN_CONTENT_CHARS:
        raise ValueError(
            f"Please provide at least {MIN_CONTENT_CHARS} characters of content for the AI to work with."
        )
    return cleaned


def validate_quiz_source(source: str) -> None:
    if source not in (SOURCE_TOPIC, SOURCE_PDF):
        raise ValueError(f"Unknown quiz source: {source}")
