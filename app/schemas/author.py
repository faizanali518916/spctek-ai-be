import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AuthorBase(BaseModel):
    name: str
    profile_picture_url: str | None = None
    about: str | None = None
    organization: str | None = None
    position: str | None = None
    social_links: dict[str, str] = Field(default_factory=dict)


class AuthorCreate(AuthorBase):
    pass


class AuthorUpdate(AuthorBase):
    name: str | None = None


class AuthorRead(AuthorBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
