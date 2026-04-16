import logging
import tempfile
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.reinstatement import (
    ReportRequest,
    ReportResponse,
    ReinstatementLogCreateRequest,
    ReinstatementLogResponse,
    ReinstatementLogsListResponse,
    GenerateReportFromLogRequest,
)
from app.services.reinstatement import generate_report
from app.services.formatter import write_formatted_report
from app.services.email import send_reinstatement_report_email
from app.database import get_db
from app.models.reinstatement_log import ReinstatementLog
from app.models.contact import Contact

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
            "Report request received: business_model=%s, recipient_email=%s",
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


@router.post("/logs", response_model=ReinstatementLogResponse)
async def create_reinstatement_log(
    payload: ReinstatementLogCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new reinstatement log with form data.

    This endpoint saves all the form data from the reinstatement estimator
    for record keeping and later report generation.
    """
    try:
        logger.info(f"Creating reinstatement log for contact: {payload.contact_id}")

        # Verify contact exists
        result = await db.execute(select(Contact).where(Contact.id == payload.contact_id))
        contact = result.scalar_one_or_none()

        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found",
            )

        # Create and save the log
        log = ReinstatementLog(
            contact_id=payload.contact_id,
            performance_notification=payload.performance_notification,
            suspension_date=payload.suspension_date,
            business_model=payload.business_model,
            fulfillment_channel=payload.fulfillment_channel,
            appeals_made=payload.appeals_made,
            seller_belief=payload.seller_belief,
            available_documents=payload.available_documents,
        )

        db.add(log)
        await db.commit()
        await db.refresh(log)

        logger.info(f"Reinstatement log created successfully: {log.id}")
        return ReinstatementLogResponse.from_orm(log)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reinstatement log: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reinstatement log",
        )


@router.get("/logs/{contact_id}", response_model=ReinstatementLogsListResponse)
async def list_reinstatement_logs(
    contact_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all reinstatement logs for a specific contact.

    Returns all logs associated with the given contact ID, useful for
    viewing submission history in the portal.
    """
    try:
        logger.info(f"Listing reinstatement logs for contact: {contact_id}")

        # Verify contact exists
        result = await db.execute(select(Contact).where(Contact.id == contact_id))
        contact = result.scalar_one_or_none()

        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found",
            )

        # Get logs for this contact
        result = await db.execute(
            select(ReinstatementLog)
            .where(ReinstatementLog.contact_id == contact_id)
            .order_by(ReinstatementLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        logs = result.scalars().all()

        # Get total count
        count_result = await db.execute(select(ReinstatementLog).where(ReinstatementLog.contact_id == contact_id))
        total = len(count_result.scalars().all())

        logger.info(f"Found {len(logs)} reinstatement logs for contact {contact_id}")
        return ReinstatementLogsListResponse(
            logs=[ReinstatementLogResponse.from_orm(log) for log in logs],
            total=total,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing reinstatement logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list reinstatement logs",
        )


@router.post("/generate-from-log", response_model=ReportResponse)
async def generate_report_from_log(
    payload: GenerateReportFromLogRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Generate a reinstatement report from a saved log ID.

    This endpoint generates a report using the data from a previously
    saved reinstatement log and sends it to the associated contact's email.
    """
    try:
        logger.info(f"Generating report from log: {payload.log_id}")

        # Get the log
        result = await db.execute(select(ReinstatementLog).where(ReinstatementLog.id == payload.log_id))
        log = result.scalar_one_or_none()

        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reinstatement log not found",
            )

        # Get the associated contact
        result = await db.execute(select(Contact).where(Contact.id == log.contact_id))
        contact = result.scalar_one_or_none()

        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated contact not found",
            )

        # Generate the report using the log data
        report = generate_report(
            performance_notification=log.performance_notification,
            suspension_date=log.suspension_date,
            business_model=log.business_model,
            appeals_made=log.appeals_made,
            seller_belief=log.seller_belief,
            available_documents=log.available_documents,
        )

        logger.info(f"Report generated successfully from log {payload.log_id}")

        # Add background task to send email
        background_tasks.add_task(
            send_report_email_background,
            report_text=report,
            recipient_name=contact.name or "Customer",
            recipient_email=contact.email,
        )

        return ReportResponse(report=report)

    except HTTPException:
        raise
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
        logger.error(f"Error generating report from log: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report from log",
        )
