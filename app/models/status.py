from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Status(Base):
    __tablename__ = "statuses"

    code: Mapped[str] = mapped_column(String(50), nullable=False)

    contacts: Mapped[list["Contact"]] = relationship(
        "Contact",
        back_populates="status",
        passive_deletes=True,
    )
