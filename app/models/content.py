import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.associations import content_categories_association


class ContentType(str, enum.Enum):
    BLOG = "BLOG"
    CASE_STUDY = "CASE_STUDY"


class Content(Base):
    __tablename__ = "content"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(120), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="contenttype", create_type=False),
        nullable=False,
        default=ContentType.BLOG,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    categories: Mapped[list["Category"]] = relationship(
        secondary=content_categories_association,
        back_populates="contents",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
