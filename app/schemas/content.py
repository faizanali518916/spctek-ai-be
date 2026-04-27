import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.author import AuthorRead
from app.models.content import ContentType
from app.schemas.category import CategoryRead


class ContentBase(BaseModel):
    title: str
    slug: str
    summary: str | None = None
    thumbnail_url: str
    content: dict | list = Field(..., description="Structured JSON content from the editor")
    author_id: uuid.UUID | None = None
    type: ContentType = ContentType.BLOG
    is_published: bool = False


class ContentInput(ContentBase):
    category_ids: list[uuid.UUID] = Field(default_factory=list)


class ContentCreate(ContentInput):
    pass


class ContentUpdate(ContentInput):
    pass


class ContentRead(ContentBase):
    id: uuid.UUID
    author_id: uuid.UUID | None = None
    author: AuthorRead | None = Field(None, alias="author_rel", serialization_alias="author")
    categories: list[CategoryRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
