from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from uuid import UUID


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
    fulfillment_channel: str = Field(
        ...,
        min_length=1,
        description="Fulfillment channel (FBA or FBM).",
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


class ReinstatementLogCreateRequest(BaseModel):
    """Request body for creating a reinstatement log."""

    contact_id: UUID = Field(..., description="ID of the associated contact.")
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
        description="Seller's business model.",
    )
    fulfillment_channel: str = Field(
        ...,
        min_length=1,
        description="Fulfillment channel (FBA or FBM).",
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


class ReinstatementLogResponse(BaseModel):
    """Response body for a reinstatement log."""

    id: UUID = Field(..., description="Log ID.")
    contact_id: UUID = Field(..., description="Associated contact ID.")
    performance_notification: str
    suspension_date: str
    business_model: str
    fulfillment_channel: str
    appeals_made: int
    seller_belief: str
    available_documents: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReinstatementLogsListResponse(BaseModel):
    """Response body containing a list of reinstatement logs."""

    logs: list[ReinstatementLogResponse] = Field(..., description="List of reinstatement logs.")
    total: int = Field(..., description="Total number of logs.")


class GenerateReportFromLogRequest(BaseModel):
    """Request body for generating a report from a log ID."""

    log_id: UUID = Field(..., description="ID of the reinstatement log.")
