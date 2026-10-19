"""Ijara buyurtmalari modellari."""
import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base_mixin import TimestampMixin


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    RENTAL_ACTIVE = "rental_active"
    RENTAL_COMPLETED = "rental_completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class RentalOrder(Base, TimestampMixin):
    __tablename__ = "rental_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, native_enum=False, length=32),
        default=OrderStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # --- Buyurtma yaratilган PAYTdagi qiymatlar (muzlatilgan — keyin o'zgarmaydi) ---
    ton_uzs_rate: Mapped[float] = mapped_column(nullable=False)  # o'sha paytdagi kurs

    base_price_ton: Mapped[float] = mapped_column(nullable=False)
    commission_ton: Mapped[float] = mapped_column(default=0.0, nullable=False)
    network_fee_ton: Mapped[float] = mapped_column(default=0.0, nullable=False)
    service_fee_ton: Mapped[float] = mapped_column(default=0.0, nullable=False)
    refundable_deposit_ton: Mapped[float] = mapped_column(default=0.0, nullable=False)
    total_ton: Mapped[float] = mapped_column(nullable=False)

    # So'mdagi muzlatilgan qiymatlar
    base_price_uzs: Mapped[float] = mapped_column(nullable=False)
    total_uzs: Mapped[float] = mapped_column(nullable=False)

    # Komissiyalar tafsiloti (JSON string) — audit uchun
    commission_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ijara muddati
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    rental_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rental_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="orders")  # noqa: F821
    items: Mapped[list["RentalItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_orders_user_status", "user_id", "status"),
    )


class RentalItem(Base, TimestampMixin):
    """Buyurtmadagi NFT (bir buyurtma = bir NFT, lekin kengaytirishga tayyor)."""
    __tablename__ = "rental_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("rental_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nft_id: Mapped[int] = mapped_column(
        ForeignKey("nfts.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # NFT ma'lumotlarining snapshot'i (buyurtma vaqtida)
    nft_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    nft_name: Mapped[str] = mapped_column(String(128), nullable=False)
    nft_image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    daily_price_ton: Mapped[float] = mapped_column(nullable=False)

    order: Mapped["RentalOrder"] = relationship(back_populates="items")
