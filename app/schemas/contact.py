import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class ContactBase(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    message: str | None = None
    source: str | None = "landing_page"
    journey: dict | None = Field(default_factory=dict)


class ContactCreate(ContactBase):
    pass


class ContactUpdate(ContactBase):
    source: str | None = None


class ContactRead(ContactBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
