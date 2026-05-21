from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class Popup(Base, TimestampMixin):
    __tablename__ = "popups"

    path: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    delay: Mapped[int] = mapped_column(Integer, nullable=False)
