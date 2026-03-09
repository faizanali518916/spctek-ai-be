"""Router for Amazon reinstatement report generation."""

import logging
import tempfile
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from app.schemas.reinstatement import ReportRequest, ReportResponse
from app.services.reinstatement import generate_report
from app.services.formatter import write_formatted_report
from app.services.email import send_reinstatement_report_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reinstatement", tags=["Reinstatement"])


# Explicit OPTIONS handler for CORS preflight
@router.options("/generate")
async def options_generate():
    """Handle CORS preflight request."""
    logger.info("OPTIONS /generate preflight request received")
    return {"message": "OK"}


async def send_report_email_background(
    report_text: str,
    recipient_name: str,
    recipient_email: str,
) -> None:
    """Background task to convert report to PDF and send via email."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf_file_path = tmp_file.name

        logger.info(f"Converting report to PDF for {recipient_email}")
        write_formatted_report(report_text, pdf_file_path)

        logger.info(f"Sending PDF email to {recipient_email}")
        success = send_reinstatement_report_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            pdf_file_path=pdf_file_path,
        )

        if success:
            logger.info(f"Report successfully sent to {recipient_email}")
        else:
            logger.error(f"Failed to send report to {recipient_email}")
    except Exception as e:
        logger.error(f"Error in background email task: {str(e)}", exc_info=True)


@router.post("/generate", response_model=ReportResponse)
async def create_report(
    request: Request,
    payload: ReportRequest,
    background_tasks: BackgroundTasks,
):
    """Generate an Amazon reinstatement assessment report and email as PDF.

    Accepts structured seller information and returns a markdown
    report with root-cause analysis, document comparison, reinstatement
    chance percentages, and recommended next steps. Also sends the report
    as a PDF via email to the provided address.
    """
    try:
        logger.info(
            "Report request received: model=%s, business_model=%s, recipient_email=%s",
            payload.model_selected,
            payload.business_model,
            payload.recipient_email,
        )
        logger.debug(f"Request headers: {dict(request.headers)}")

        report = generate_report(
            performance_notification=payload.performance_notification,
            suspension_date=payload.suspension_date,
            business_model=payload.business_model,
            appeals_made=payload.appeals_made,
            seller_belief=payload.seller_belief,
            available_documents=payload.available_documents,
            recipient_name=payload.recipient_name,
            recipient_email=payload.recipient_email,
            recipient_phone=payload.recipient_phone,
            model=payload.model_selected,
        )

        logger.info("Report generated successfully, adding email task to background")

        # Add background task to send email
        background_tasks.add_task(
            send_report_email_background,
            report_text=report,
            recipient_name=payload.recipient_name,
            recipient_email=payload.recipient_email,
        )

        logger.info("Report endpoint returning response")
        return ReportResponse(report=report)

    except ValueError as ve:
        logger.error("Validation error: %s", ve, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except RuntimeError as re:
        logger.error("Service error: %s", re, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        logger.error("Unexpected error generating report: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report. Please try again later.",
        )
