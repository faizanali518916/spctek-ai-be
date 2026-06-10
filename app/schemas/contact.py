import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class ContactBase(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    status_id: uuid.UUID | None = None
    phone: str | None = None
    company: str | None = None
    message: str | None = None
    source: str | None = "landing_page"
    journey: dict | None = Field(default_factory=dict)


class ContactCreate(ContactBase):
    email: EmailStr


class ContactUpdate(ContactBase):
    email: EmailStr | None = None
    source: str | None = None


class ContactSubmissionRead(BaseModel):
    id: uuid.UUID
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    message: str | None = None
    source: str | None = None
    journey: dict | None = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
        populate_by_name = True


class ContactRead(ContactBase):
    id: uuid.UUID
    status_code: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    submissions: list[ContactSubmissionRead] | None = None

    class Config:
        from_attributes = True
        populate_by_name = True
