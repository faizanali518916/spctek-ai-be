import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BlogBase(BaseModel):
    title: str
    slug: str
    summary: str | None = None
    thumbnail_url: str
    content: str
    author: str | None = None
    is_published: bool = False


class BlogCreate(BlogBase):
    pass


class BlogUpdate(BaseModel):
    title: str
    slug: str
    summary: str | None = None
    thumbnail_url: str
    content: str
    author: str | None = None
    is_published: bool = False


class BlogRead(BlogBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
