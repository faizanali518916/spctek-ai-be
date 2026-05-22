import json
import logging
import time
from typing import Any, Optional

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2.0


def _get_client() -> genai.Client:
    settings = get_settings()
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not configured.")
    return genai.Client(api_key=api_key)


def _extract_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return text

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                return part_text

    raise RuntimeError("Gemini returned no text content")


def generate(
    prompt: Optional[str] = None,
    *,
    system: Optional[str] = None,
    user: Optional[str] = None,
) -> dict[str, Any]:
    """Request JSON from Gemini and return it as a parsed dict."""
    client = _get_client()

    contents = user if user is not None else prompt
    if not contents:
        raise ValueError("generate() requires prompt or user content")

    config = types.GenerateContentConfig(
        systemInstruction=system,
        responseMimeType="application/json",
        temperature=0.0,
    )

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            text = _extract_text(response)
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`")
            return json.loads(text)
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Gemini generation failed (attempt %s/%s, model=%s): %s",
                attempt,
                MAX_RETRIES,
                GEMINI_MODEL,
                exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
                continue
            break

    raise RuntimeError(f"Gemini generation failed after {MAX_RETRIES} attempts: {last_error}")
