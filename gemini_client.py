import json
import os
import re

import google.generativeai as genai

from config import GEMINI_MODELS


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


def generate_content(prompt: str) -> str:
    last_error = None
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(friendly_api_error(last_error or RuntimeError("No model available")))
