import uuid

from pydantic import BaseModel, ConfigDict, Field


class StatusBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)


class StatusCreate(StatusBase):
    pass


class StatusUpdate(StatusBase):
    pass


class StatusRead(StatusBase):
    id: uuid.UUID
    contact_count: int = 0

    model_config = ConfigDict(from_attributes=True)
