"""Pydantic sxemalar (so'rov / javob modellari)."""
from datetime import datetime

from pydantic import BaseModel, Field


# ---------- Auth ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    password_confirm: str = Field(min_length=6, max_length=128)
    init_data: str | None = None  # Telegram WebApp initData
    language: str = "uz"


class LoginIn(BaseModel):
    username: str
    password: str


class TelegramAuthIn(BaseModel):
    """Telegram WebApp initData orqali avtomatik autentifikatsiya."""
    init_data: str
    language: str = "uz"


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)
    new_password_confirm: str = Field(min_length=6, max_length=128)


class LanguageIn(BaseModel):
    language: str = Field(pattern="^(uz|en)$")


class TokenOut(BaseModel):
    token: str
    username: str
    language: str


# ---------- Profil ----------
class ProfileOut(BaseModel):
    id: int
    username: str
    language: str
    balance_uzs: float
    created_at: datetime
    support_username: str


# ---------- NFT ----------
class NftOut(BaseModel):
    id: int
    nft_ref: str
    name: str
    image_url: str
    collection_name: str | None
    daily_price_ton: float
    daily_price_uzs: float
    allowed_durations: list[int]
    is_available: bool
    is_popular: bool
    source: str


class NftDetailOut(NftOut):
    description: str | None = None


# ---------- Narx hisob-kitobi ----------
class QuoteIn(BaseModel):
    nft_id: int
    duration_days: int


class CommissionLineOut(BaseModel):
    kind: str
    label_uz: str
    label_en: str
    calc_type: str
    value: float
    amount_ton: float
    amount_uzs: float
    refundable: bool


class QuoteOut(BaseModel):
    nft_id: int
    daily_price_ton: float
    duration_days: int
    base_price_ton: float
    base_price_uzs: float
    commission_ton: float
    network_fee_ton: float
    service_fee_ton: float
    refundable_deposit_ton: float
    total_ton: float
    total_uzs: float
    ton_uzs_rate: float
    lines: list[CommissionLineOut]


# ---------- Buyurtma ----------
class CreateOrderIn(BaseModel):
    nft_id: int
    duration_days: int


class OrderOut(BaseModel):
    id: int
    order_number: str
    status: str
    duration_days: int
    base_price_ton: float
    total_ton: float
    base_price_uzs: float
    total_uzs: float
    ton_uzs_rate: float
    rental_start_at: datetime | None
    rental_end_at: datetime | None
    created_at: datetime
    nft_name: str | None = None
    nft_image_url: str | None = None
    payment_note: str


# ---------- Admin ----------
class RateIn(BaseModel):
    rate: float = Field(gt=0)


class NftAdminIn(BaseModel):
    nft_ref: str
    name: str
    image_url: str
    collection_id: int | None = None
    daily_price_ton: float = Field(ge=0)
    allowed_durations: list[int] = [1, 3, 7, 30]
    is_available: bool = True
    is_hidden: bool = False
    is_popular: bool = False


class SupportIn(BaseModel):
    support_username: str = Field(min_length=1, max_length=64)


class PaymentSettingsIn(BaseModel):
    # ⚠️ Faqat ochiq manzil. Seed/private key QABUL QILINMAYDI.
    receiving_address: str | None = Field(default=None, max_length=128)
    tonconnect_manifest_url: str | None = Field(default=None, max_length=255)
    payments_enabled: bool | None = None


class CommissionIn(BaseModel):
    kind: str
    calc_type: str
    value: float
    order_index: int = 0
    is_active: bool = True
    label_uz: str = ""
    label_en: str = ""
