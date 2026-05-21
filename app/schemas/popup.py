import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PopupContent(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    cta_text: str = Field(min_length=1)
    cta_link: str = Field(min_length=1)


class PopupBase(BaseModel):
    path: str = Field(min_length=1)
    content: PopupContent
    delay: int = Field(ge=0)


class PopupCreate(PopupBase):
    pass


class PopupUpdate(BaseModel):
    path: str | None = Field(default=None, min_length=1)
    content: PopupContent | None = None
    delay: int | None = Field(default=None, ge=0)


class PopupRead(PopupBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
