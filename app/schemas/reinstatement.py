"""Schemas for the reinstatement report endpoint."""

from pydantic import BaseModel, Field, EmailStr


class ReportRequest(BaseModel):
    """Request body for generating a reinstatement report."""

    performance_notification: str = Field(
        ...,
        min_length=1,
        description="Full text of the Amazon Performance Notification.",
    )
    suspension_date: str = Field(
        ...,
        min_length=1,
        description="Date of account suspension (e.g. 2024-03-15).",
    )
    business_model: str = Field(
        ...,
        min_length=1,
        description="Seller's business model (e.g. Private Label, Wholesale).",
    )
    appeals_made: int = Field(
        default=0,
        ge=0,
        description="Number of previous appeal attempts.",
    )
    seller_belief: str = Field(
        ...,
        min_length=1,
        description="Seller's own explanation for the suspension.",
    )
    available_documents: str = Field(
        ...,
        min_length=1,
        description="Comma-separated list of available documents.",
    )
    model_selected: str = Field(
        default="gemini-3-flash-preview",
        description="Gemini model to use for generation.",
    )
    # Contact information for sending report via email
    recipient_name: str = Field(
        ...,
        min_length=1,
        description="Name of the recipient for the report.",
    )
    recipient_email: EmailStr = Field(
        ...,
        description="Email address to send the report to.",
    )
    recipient_phone: str | None = Field(
        default=None,
        description="Optional phone number of the recipient.",
    )


class ReportResponse(BaseModel):
    """Response body containing the generated report."""

    report: str = Field(..., description="The generated markdown report.")
