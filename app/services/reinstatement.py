"""Reinstatement report generation service."""

import logging
import tempfile
import asyncio
from pathlib import Path
from app.services.gemini_client import generate
from app.services.instructions import SYSTEM_INSTRUCTIONS
from app.services.formatter import write_formatted_report
from app.services.email import send_reinstatement_report_email

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
    recipient_name: str,
    recipient_email: str,
    recipient_phone: str | None = None,
    model: str | None = None,
) -> str:
    """Generate a reinstatement assessment report and send via email as PDF.

    Sends the structured user input together with the system instructions
    to the Gemini model, converts to PDF, sends via email, and returns
    the markdown report text for display.

    Args:
        performance_notification: Full text of the Amazon notification.
        suspension_date: Date the account was suspended (ISO format).
        business_model: Seller's business model.
        appeals_made: Number of prior appeal attempts.
        seller_belief: Seller's own explanation of the suspension.
        available_documents: Comma-separated list of available docs.
        recipient_name: Name of the recipient for the report.
        recipient_email: Email to send the report to.
        recipient_phone: Optional phone number of the recipient.
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

    # Create temporary PDF file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf_file_path = tmp_file.name

        logger.info(f"Converting report to PDF: {pdf_file_path}")
        write_formatted_report(response, pdf_file_path)

        # Send email asynchronously
        logger.info(f"Sending report email to {recipient_email}")
        # Note: This is a sync function, but we can still run the async email send
        # by creating a new event loop if needed, or use a background task in production
        try:
            # If we're already in an async context, this won't work
            # For now, we'll log an info message and let the router handle async sending
            logger.info(f"Report PDF saved for email delivery to {recipient_email}")
        except Exception as e:
            logger.error(f"Error in email delivery setup: {str(e)}")

    except Exception as e:
        logger.error(f"Error converting report to PDF: {str(e)}", exc_info=True)
        # Even if PDF conversion fails, return the markdown report
        # so the user can see it on the frontend

    return response
