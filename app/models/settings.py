"""Sozlamalar modellari: valyuta kursi, komissiyalar, support, adminlar."""
import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base_mixin import TimestampMixin


class CurrencySetting(Base):
    """TON/UZS kursi tarixi. Eng so'nggi yozuv = joriy kurs."""
    __tablename__ = "currency_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    ton_uzs_rate: Mapped[float] = mapped_column(nullable=False)
    changed_by_admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class CommissionType(str, enum.Enum):
    PERCENT = "percent"       # asosiy narxdan foiz
    FLAT_TON = "flat_ton"     # qat'iy TON qiymat


class CommissionKind(str, enum.Enum):
    MARKETPLACE = "marketplace"       # Marketplace komissiyasi
    NETWORK = "network"               # TON tarmog'i tranzaksiya xarajati
    SERVICE = "service"               # Xizmat / shartnoma xarajati
    REFUNDABLE_DEPOSIT = "refundable_deposit"  # Qaytariladigan depozit


class CommissionSetting(Base, TimestampMixin):
    """Komissiya turlari — admin sozlaydi."""
    __tablename__ = "commission_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[CommissionKind] = mapped_column(
        SAEnum(CommissionKind, native_enum=False, length=32), nullable=False, index=True
    )
    calc_type: Mapped[CommissionType] = mapped_column(
        SAEnum(CommissionType, native_enum=False, length=16), nullable=False
    )
    value: Mapped[float] = mapped_column(nullable=False, default=0.0)  # foiz (masalan 5.0) yoki TON
    order_index: Mapped[int] = mapped_column(default=0, nullable=False)  # hisoblash tartibi
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    label_uz: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    label_en: Mapped[str] = mapped_column(String(128), default="", nullable=False)


class SupportSetting(Base):
    """Support username — bitta yozuv (id=1) ishlatiladi."""
    __tablename__ = "support_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    support_username: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PaymentSetting(Base):
    """
    TON to'lov sozlamalari — bitta yozuv (id=1).

    ⚠️ XAVFSIZLIK: Bu yerda FAQAT ochiq (public) qabul qiluvchi manzil saqlanadi.
    Seed phrase yoki private key HECH QACHON saqlanmaydi!
    To'lovni foydalanuvchi o'z hamyonida (Tonkeeper / TON Connect) imzolaydi.
    """
    __tablename__ = "payment_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Qabul qiluvchi TON manzili (UQ.../EQ...) — ochiq, admin o'zgartiradi
    receiving_address: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    # TON Connect manifest URL (WebApp uchun)
    tonconnect_manifest_url: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    # To'lov tizimi yoqilganmi (admin boshqaradi; boshida o'chiq)
    payments_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Minimal tasdiqlash: necha sekund kutib blockchain tekshiriladi
    confirmation_timeout_seconds: Mapped[int] = mapped_column(default=600, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AdminUser(Base, TimestampMixin):
    """Admin rollar — Telegram ID orqali (config bilan birga ishlatiladi)."""
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
