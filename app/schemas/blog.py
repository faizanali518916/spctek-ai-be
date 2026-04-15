import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead


class BlogBase(BaseModel):
    title: str
    slug: str
    summary: str | None = None
    thumbnail_url: str
    content: str
    author: str | None = None
    is_published: bool = False


class BlogInput(BlogBase):
    category_ids: list[uuid.UUID] = Field(default_factory=list)


class BlogCreate(BlogInput):
    pass


class BlogUpdate(BlogInput):
    pass


class BlogRead(BlogBase):
    id: uuid.UUID
    categories: list[CategoryRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
