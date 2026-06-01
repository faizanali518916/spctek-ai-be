import enum

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin
from app.models.category import Category
from app.models.associations import automation_workflow_categories_association


class AutomationWorkflowClass(str, enum.Enum):
    SYSTEM = "system"
    PLUGIN = "plugin"


class AutomationWorkflow(Base, TimestampMixin):
    __tablename__ = "automation_workflows"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    teaser: Mapped[str] = mapped_column(String(500), nullable=False)
    workflow_class: Mapped[AutomationWorkflowClass] = mapped_column(
        "class",
        Enum(
            AutomationWorkflowClass,
            name="automationworkflowclass",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
    )
    description: Mapped[dict] = mapped_column(JSONB, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    categories: Mapped[list["Category"]] = relationship(
        secondary=automation_workflow_categories_association,
        back_populates="automation_workflows",
    )
