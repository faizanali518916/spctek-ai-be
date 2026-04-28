import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MetadeckBase(BaseModel):
    path: str
    title: str
    description: str


class MetadeckCreate(MetadeckBase):
    pass


class MetadeckUpdate(MetadeckBase):
    path: str | None = None
    title: str | None = None
    description: str | None = None


class MetadeckRead(MetadeckBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
