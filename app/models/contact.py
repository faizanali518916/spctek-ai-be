import uuid
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base, TimestampMixin


class Contact(Base):
    __tablename__ = "contacts"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    submissions: Mapped[list["ContactSubmission"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan"
    )


class ContactSubmission(Base, TimestampMixin):
    __tablename__ = "contact_submissions"

    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, default="landing_page")
    journey: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=lambda: {})

    contact: Mapped["Contact"] = relationship(back_populates="submissions")
