from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin
from app.models.associations import automation_workflow_categories_association, content_categories_association


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    contents: Mapped[list["Content"]] = relationship(
        secondary=content_categories_association,
        back_populates="categories",
    )
    automation_workflows: Mapped[list["AutomationWorkflow"]] = relationship(
        secondary=automation_workflow_categories_association,
        back_populates="categories",
    )
