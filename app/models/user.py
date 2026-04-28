from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base, TimestampMixin
import enum


class UserRole(str, enum.Enum):
    BASIC = "BASIC"
    ADMIN = "ADMIN"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    user_role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.BASIC)
