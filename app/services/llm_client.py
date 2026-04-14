import logging
from openai import OpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"


def _get_client() -> OpenAI:
    """Create an OpenAI-compatible client for OpenRouter."""
    settings = get_settings()

    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


def generate(prompt: str) -> str:
    """Generate content using the best free model available."""
    target_model = "openrouter/free"
    client = _get_client()

    logger.info("Generating content via OpenRouter (Free Tier) with model: %s", target_model)
    try:
        response = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenRouter returned an empty response.")

        return content

    except Exception as e:
        logger.error("OpenRouter API error: %s", e)
        raise RuntimeError(f"OpenRouter API error: {e}") from e
