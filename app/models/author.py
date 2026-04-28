from typing import List

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class Author(Base, TimestampMixin):
    __tablename__ = "authors"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500))
    about: Mapped[str | None] = mapped_column(Text)
    organization: Mapped[str | None] = mapped_column(String(255))
    position: Mapped[str | None] = mapped_column(String(255))

    social_links: Mapped[dict | None] = mapped_column(JSONB, default={})

    # Relationship with Content
    contents: Mapped[List["Content"]] = relationship("Content", back_populates="author_rel")
