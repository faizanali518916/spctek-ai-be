"""Gemini API client for the reinstatement service."""

import logging
from google import genai
from app.config import get_settings

logger = logging.getLogger(__name__)

# Available Gemini models
AVAILABLE_MODELS = [
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

DEFAULT_MODEL = "gemini-3-flash-preview"


def _get_client() -> genai.Client:
    """Create a Gemini client using the API key from settings."""
    settings = get_settings()
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not configured in environment.")
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def generate(prompt: str, model: str | None = None) -> str:
    """Generate content using the specified Gemini model.

    Args:
        prompt: The prompt to send to the model.
        model: The model identifier (defaults to DEFAULT_MODEL).

    Returns:
        The generated text response.

    Raises:
        ValueError: If the API key is missing.
        RuntimeError: If the Gemini API call fails.
    """
    model = model or DEFAULT_MODEL
    client = _get_client()

    logger.info("Generating content with model: %s", model)
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except Exception as e:
        logger.error("Gemini API error with model %s: %s", model, e)
        raise RuntimeError(f"Gemini API error: {e}") from e
