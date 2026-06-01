import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.automation_workflow import AutomationWorkflowClass
from app.schemas.category import CategoryRead


class AutomationWorkflowDescription(BaseModel):
    body: str = Field(min_length=1)
    bullets: list[str] = Field(default_factory=list)


class AutomationWorkflowBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    teaser: str = Field(min_length=1, max_length=500)
    workflow_class: AutomationWorkflowClass = Field(alias="class")
    description: AutomationWorkflowDescription
    link: str | None = Field(default=None, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(populate_by_name=True)


class AutomationWorkflowCreate(AutomationWorkflowBase):
    category_ids: list[uuid.UUID] = Field(default_factory=list)


class AutomationWorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    teaser: str | None = Field(default=None, min_length=1, max_length=500)
    workflow_class: AutomationWorkflowClass | None = Field(default=None, alias="class")
    description: AutomationWorkflowDescription | None = None
    link: str | None = Field(default=None, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    category_ids: list[uuid.UUID] | None = None

    model_config = ConfigDict(populate_by_name=True)


class AutomationWorkflowRead(AutomationWorkflowBase):
    id: uuid.UUID
    categories: list[CategoryRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)
