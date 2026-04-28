import uuid
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, TimestampMixin


class ReinstatementLog(Base, TimestampMixin):
    __tablename__ = "reinstatement_logs"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    performance_notification: Mapped[str] = mapped_column(Text, nullable=False)
    suspension_date: Mapped[str] = mapped_column(String(20), nullable=False)
    business_model: Mapped[str] = mapped_column(String(100), nullable=False)
    fulfillment_channel: Mapped[str] = mapped_column(String(50), nullable=False)
    appeals_made: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seller_belief: Mapped[str] = mapped_column(Text, nullable=False)
    available_documents: Mapped[str] = mapped_column(Text, nullable=False)

    contact: Mapped["Contact"] = relationship("Contact", foreign_keys=[contact_id])
