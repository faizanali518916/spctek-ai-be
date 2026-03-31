import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BlogBase(BaseModel):
    title: str
    slug: str
    summary: str | None = None
    content: str
    author: str | None = None
    is_published: bool = False


class BlogCreate(BlogBase):
    pass


class BlogUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    summary: str | None = None
    content: str | None = None
    author: str | None = None
    is_published: bool | None = None


class BlogRead(BlogBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
