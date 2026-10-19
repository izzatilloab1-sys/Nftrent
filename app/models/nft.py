"""NFT to'plam va NFT modellari."""
from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base_mixin import TimestampMixin


class NftCollection(Base, TimestampMixin):
    __tablename__ = "nft_collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    nfts: Mapped[list["Nft"]] = relationship(back_populates="collection")


class Nft(Base, TimestampMixin):
    __tablename__ = "nfts"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Tashqi NFT identifikatori (Marketapp / TON) — ko'rsatiladigan ID
    nft_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)

    collection_id: Mapped[int | None] = mapped_column(
        ForeignKey("nft_collections.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Narx (asosiy valyuta — TON; so'm serverdagi kurs orqali hisoblanadi)
    daily_price_ton: Mapped[float] = mapped_column(nullable=False)

    # Ruxsat etilgan ijara muddatlari (kunlarda), JSON string: "[1,3,7,30]"
    allowed_durations: Mapped[str] = mapped_column(String(128), default="[1,3,7,30]", nullable=False)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # admin yashirgan
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Manba: demo | marketapp  — demo NFT'lar haqiqiy deb ko'rsatilmaydi
    source: Mapped[str] = mapped_column(String(32), default="demo", nullable=False)

    collection: Mapped["NftCollection | None"] = relationship(back_populates="nfts")

    __table_args__ = (
        Index("ix_nfts_available_hidden", "is_available", "is_hidden"),
    )
