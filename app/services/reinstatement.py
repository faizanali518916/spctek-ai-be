import logging
import tempfile
from app.services.llm_client import generate
from app.services.formatter import write_formatted_report
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
) -> str:
    """Generate a reinstatement assessment report and send via email as PDF.

    Sends the structured user input together with the system instructions
    to the LLM model, converts to PDF, sends via email, and returns
    the markdown report text for display.

    Args:
        performance_notification: Full text of the Amazon notification.
        suspension_date: Date the account was suspended (ISO format).
        business_model: Seller's business model.
        appeals_made: Number of prior appeal attempts.
        seller_belief: Seller's own explanation of the suspension.
        available_documents: Comma-separated list of available docs.

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

    response = generate(prompt)
    logger.info("Reinstatement report generated successfully")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf_file_path = tmp_file.name

        logger.info(f"Converting report to PDF: {pdf_file_path}")
        write_formatted_report(response, pdf_file_path)

    except Exception as e:
        logger.error(f"Error converting report to PDF: {str(e)}", exc_info=True)

    return response
