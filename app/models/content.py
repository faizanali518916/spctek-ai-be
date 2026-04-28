import enum
import uuid

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, Enum, ForeignKey, String

from app.database import Base, TimestampMixin
from app.models.author import Author
from app.models.category import Category
from app.models.associations import content_categories_association


class ContentType(str, enum.Enum):
    BLOG = "BLOG"
    CASE_STUDY = "CASE_STUDY"


class Content(Base, TimestampMixin):
    __tablename__ = "content"

    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)

    summary: Mapped[str | None] = mapped_column(String(500), nullable=False)
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
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("authors.id"), nullable=True)
    author_rel: Mapped["Author"] = relationship("Author", back_populates="contents")
