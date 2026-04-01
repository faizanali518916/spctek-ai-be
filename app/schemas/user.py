import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from enum import Enum


class UserRole(str, Enum):
    BASIC = "BASIC"
    ADMIN = "ADMIN"


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    user_role: UserRole = UserRole.BASIC


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    user_role: UserRole
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserRead
