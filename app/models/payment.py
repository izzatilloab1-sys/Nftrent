"""To'lov urinishlari modeli — hozircha DEMO rejimda (real to'lov yo'q)."""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentStatus(str, enum.Enum):
    DEMO = "demo"            # to'lov tizimi hali ulanmagan
    INITIATED = "initiated"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class PaymentAttempt(Base):
    """
    Kelajakdagi to'lov integratsiyasi uchun tayyor jadval.
    Hozircha faqat 'demo' yozuvlar yaratiladi, real to'lov amalga oshmaydi.
    """
    __tablename__ = "payment_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("rental_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(32), default="none", nullable=False)  # ton | uzs | none
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, native_enum=False, length=16),
        default=PaymentStatus.DEMO,
        nullable=False,
        index=True,
    )
    # Idempotentlik: bir buyurtma bir marta tasdiqlansin
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    amount_ton: Mapped[float] = mapped_column(default=0.0, nullable=False)
    external_tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
