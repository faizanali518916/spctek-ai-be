from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

content_categories_association = Table(
    "content_categories",
    Base.metadata,
    Column("content_id", UUID(as_uuid=True), ForeignKey("content.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)

automation_workflow_categories_association = Table(
    "automation_workflow_categories",
    Base.metadata,
    Column(
        "automation_workflow_id",
        UUID(as_uuid=True),
        ForeignKey("automation_workflows.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("category_id", UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)
