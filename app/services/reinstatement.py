"""Reinstatement report generation service."""

import logging
from app.services.gemini_client import generate
from app.services.instructions import SYSTEM_INSTRUCTIONS

logger = logging.getLogger(__name__)


def build_user_prompt(
    performance_notification: str,
    suspension_date: str,
    business_model: str,
    appeals_made: int,
    seller_belief: str,
    available_documents: str,
) -> str:
    """Combine form fields into a single structured prompt."""
    return f"""
**Performance Notification:**
{performance_notification}

**Suspension Date:** {suspension_date}

**Business Model:** {business_model}

**Previous Appeals:** {appeals_made}

**Seller's Belief on Suspension Cause:**
{seller_belief}

**Available Documents:**
{available_documents}
""".strip()


def generate_report(
    performance_notification: str,
    suspension_date: str,
    business_model: str,
    appeals_made: int,
    seller_belief: str,
    available_documents: str,
    model: str | None = None,
) -> str:
    """Generate a reinstatement assessment report.

    Sends the structured user input together with the system instructions
    to the Gemini model and returns the raw markdown report text.

    Args:
        performance_notification: Full text of the Amazon notification.
        suspension_date: Date the account was suspended (ISO format).
        business_model: Seller's business model.
        appeals_made: Number of prior appeal attempts.
        seller_belief: Seller's own explanation of the suspension.
        available_documents: Comma-separated list of available docs.
        model: Optional Gemini model override.

    Returns:
        The generated markdown report.
    """
    user_input = build_user_prompt(
        performance_notification=performance_notification,
        suspension_date=suspension_date,
        business_model=business_model,
        appeals_made=appeals_made,
        seller_belief=seller_belief,
        available_documents=available_documents,
    )

    prompt = f"""
{SYSTEM_INSTRUCTIONS}

INPUT
{user_input}

Respond strictly in the defined format.
"""

    logger.info("Sending reinstatement prompt to Gemini (model=%s)", model)
    response = generate(prompt, model=model)
    logger.info("Reinstatement report generated successfully")
    return response
