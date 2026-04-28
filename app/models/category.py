from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin
from app.models.associations import content_categories_association


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    contents: Mapped[list["Content"]] = relationship(
        secondary=content_categories_association,
        back_populates="categories",
    )
