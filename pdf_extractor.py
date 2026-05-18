import io

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract readable text from a PDF file.
    Uses pypdf (maintained fork of PyPDF2).
    """
    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Could not read PDF file. It may be corrupted or password-protected. ({exc})") from exc

    if len(reader.pages) == 0:
        raise ValueError("The PDF has no pages.")

    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text.strip())

    full_text = "\n\n".join(parts).strip()
    if not full_text:
        raise ValueError(
            "No text could be extracted from this PDF. "
            "It may be scanned images only — try a text-based PDF."
        )

    return full_text
