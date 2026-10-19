"""Foydalanuvchi, sessiya va login urinishlari modellari."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base_mixin import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Telegram bilan bog'lash (initData dan)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True, index=True)

    language: Mapped[str] = mapped_column(String(2), default="uz", nullable=False)  # uz | en
    balance_uzs: Mapped[float] = mapped_column(default=0.0, nullable=False)  # faqat ko'rsatish uchun
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["RentalOrder"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa: F821

    __table_args__ = (
        Index("ix_users_telegram_active", "telegram_id", "is_active"),
    )


class Session(Base):
    """Login sessiyalari (JWT jti ro'yxati — bekor qilish uchun)."""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")


class LoginAttempt(Base):
    """Login urinishlari — rate limiting uchun."""
    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
