"""Router for Amazon reinstatement report generation."""

import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.reinstatement import ReportRequest, ReportResponse
from app.services.reinstatement import generate_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reinstatement", tags=["Reinstatement"])


@router.post("/generate", response_model=ReportResponse)
async def create_report(payload: ReportRequest):
    """Generate an Amazon reinstatement assessment report.

    Accepts structured seller information and returns a markdown
    report with root-cause analysis, document comparison, reinstatement
    chance percentages, and recommended next steps.
    """
    try:
        logger.info(
            "Report request: model=%s, business_model=%s",
            payload.model_selected,
            payload.business_model,
        )

        report = generate_report(
            performance_notification=payload.performance_notification,
            suspension_date=payload.suspension_date,
            business_model=payload.business_model,
            appeals_made=payload.appeals_made,
            seller_belief=payload.seller_belief,
            available_documents=payload.available_documents,
            model=payload.model_selected,
        )

        return ReportResponse(report=report)

    except ValueError as ve:
        logger.error("Validation error: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except RuntimeError as re:
        logger.error("Service error: %s", re)
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
