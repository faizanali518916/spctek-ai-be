import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class ContactCreate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    message: str | None = None
    source: str | None = "landing_page"


class ContactRead(BaseModel):
    id: uuid.UUID
    name: str | None
    email: str | None
    phone: str | None
    company: str | None
    message: str | None
    source: str | None
    created_at: datetime

    class Config:
        from_attributes = True
