import os
import json
import logging
from time import perf_counter
from datetime import datetime
from pathlib import Path

from app.services.llm_client import generate
from app.services.formatter import write_formatted_report
from app.services.instructions import SYSTEM_INSTRUCTIONS

logger = logging.getLogger(__name__)
OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"


def _log_duration(step: str, started_at: float) -> None:
    logger.warning("TIMING | %s: %.2fs", step, perf_counter() - started_at)


def build_user_prompt(
    performance_notification: str,
    suspension_date: str,
    business_model: str,
    fulfillment_channel: str,
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

Fulfillment Channel: {fulfillment_channel}

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
    fulfillment_channel: str,
    appeals_made: int,
    seller_belief: str,
    available_documents: str,
) -> dict:
    """Generate a reinstatement assessment report.

    Sends all structured seller input to the LLM and returns the parsed
    JSON report. Also writes a PDF copy to a temp file.
    """
    total_started = perf_counter()

    step_started = perf_counter()
    user_prompt = build_user_prompt(
        performance_notification=performance_notification,
        suspension_date=suspension_date,
        business_model=business_model,
        fulfillment_channel=fulfillment_channel,
        appeals_made=appeals_made,
        seller_belief=seller_belief,
        available_documents=available_documents,
    )
    _log_duration("Prompt assembly", step_started)

    step_started = perf_counter()
    response = generate(
        system=SYSTEM_INSTRUCTIONS,
        user=user_prompt,
    )
    _log_duration("Gemini generation", step_started)

    step_started = perf_counter()
    if isinstance(response, dict):
        report = response
    else:
        try:
            report = json.loads(response)
        except Exception as e:
            logger.error("LLM returned invalid JSON or unexpected type", exc_info=True)
            raise ValueError("Failed to parse LLM response as JSON") from e

    _log_duration("Response parsing", step_started)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    step_started = perf_counter()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUTS_DIR / f"report_{timestamp}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("JSON report saved: %s", json_path)
    _log_duration("JSON write", step_started)

    try:
        step_started = perf_counter()
        pdf_path = OUTPUTS_DIR / f"report_{timestamp}.pdf"
        logger.info("Converting report to PDF: %s", pdf_path)
        write_formatted_report(report, str(pdf_path))
        _log_duration("PDF render", step_started)
    except Exception as e:
        logger.error(f"Error converting report to PDF: {e}", exc_info=True)

    _log_duration("Total reinstatement generation", total_started)
    return report
