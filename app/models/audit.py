"""Audit log — muhim admin harakatlari."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
