import os
import json
import logging
import tempfile
from datetime import datetime

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
Performance Notification:
{performance_notification}

Suspension Date: {suspension_date}

Business Model: {business_model}

Previous Appeals: {appeals_made}

Seller's Belief on Suspension Cause:
{seller_belief}

Available Documents:
{available_documents}
""".strip()


def generate_report(
    performance_notification: str,
    suspension_date: str,
    business_model: str,
    appeals_made: int,
    seller_belief: str,
    available_documents: str,
) -> dict:
    """Generate a reinstatement assessment report.

    Sends all structured seller input to the LLM and returns the parsed
    JSON report. Also writes a PDF copy to a temp file.

    Args:
        performance_notification: Full text of the Amazon notification.
        suspension_date: Date the account was suspended (ISO format).
        business_model: Seller's business model.
        appeals_made: Number of prior appeal attempts.
        seller_belief: Seller's own explanation of the suspension.
        available_documents: Comma-separated list of available docs.

    Returns:
        The parsed report as a dict.

    Raises:
        ValueError: If the LLM response cannot be parsed as valid JSON.
    """
    user_prompt = build_user_prompt(
        performance_notification=performance_notification,
        suspension_date=suspension_date,
        business_model=business_model,
        appeals_made=appeals_made,
        seller_belief=seller_belief,
        available_documents=available_documents,
    )

    response_text = generate(
        system=SYSTEM_INSTRUCTIONS,
        user=user_prompt,
    )

    try:
        report = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}\nRaw response:\n{response_text}")
        raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e

    logger.info("Reinstatement report generated and parsed successfully")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("reports", exist_ok=True)
    json_path = os.path.join("reports", f"report_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"JSON report saved: {json_path}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf_file_path = tmp_file.name
        logger.info(f"Converting report to PDF: {pdf_file_path}")
        write_formatted_report(report, pdf_file_path)
    except Exception as e:
        logger.error(f"Error converting report to PDF: {e}", exc_info=True)

    return report
