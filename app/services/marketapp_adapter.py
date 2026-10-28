"""
Marketapp integratsiya ADAPTERI.

Bu adapter mavjud kod bazasiga haqiqiy Marketapp API'ni ulaydi.

Rejim:
  - Integratsiya O'CHIQ (default) -> DEMO: lokal bazadagi demo NFT'lar ishlatiladi.
    Demo NFT'lar HAQIQIY deb taqdim etilmaydi.
  - Integratsiya YOQILGAN (.env) -> LIVE: haqiqiy Marketapp API'dan o'qiladi.

Yoqish uchun .env da:
    MARKETAPP_INTEGRATION_ENABLED=true
    MARKETAPP_API_BASE=https://api.marketapp.ws         # haqiqiy baza URL
    MARKETAPP_API_TOKEN=<hamkorlik tokeningiz>

⚠️ Token faqat .env da saqlanadi — kodda yoki bazada emas.

ENDPOINT yo'llari pastdagi _EP lug'atida. Swagger'dagi aniq yo'llarga qarab
bu qiymatlarni moslang (yoki .env orqali override qilish mumkin emas — bu yerda).
Hozircha standart taxminiy yo'llar qo'yilgan; real yo'llar aniqlanganda shu
lug'atni yangilash kifoya — qolgan kod o'zgarmaydi.
"""
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings

# ---- Endpoint yo'llari (Swagger'ga qarab moslang) ----
# Faqat shu lug'atni real yo'llarga o'zgartirish kifoya.
_EP = {
    "rent_nfts": "/api/v1/rent/nfts",     # ijaraga mavjud NFT'lar ro'yxati
    "nft_detail": "/api/v1/rent/nfts/{id}",  # bitta NFT tafsiloti
}


@dataclass
class IntegrationStatus:
    enabled: bool
    mode: str          # "demo" | "live"
    message_uz: str
    message_en: str


def get_integration_status() -> IntegrationStatus:
    if settings.marketapp_integration_enabled and settings.marketapp_api_base and settings.marketapp_token:
        return IntegrationStatus(
            enabled=True,
            mode="live",
            message_uz="Marketapp integratsiyasi yoqilgan (haqiqiy NFT'lar).",
            message_en="Marketapp integration is enabled (live NFTs).",
        )
    return IntegrationStatus(
        enabled=False,
        mode="demo",
        message_uz=(
            "⚠️ Marketapp integratsiyasi o'chiq. "
            "Ko'rsatilayotgan NFT'lar — demo (test) ma'lumotlari."
        ),
        message_en=(
            "⚠️ Marketapp integration is off. "
            "The NFTs shown are demo (test) data."
        ),
    )


def _headers() -> dict[str, str]:
    """Autentifikatsiya sarlavhasi. Swagger'dagi usulga qarab moslang.

    Ko'pchilik API: Authorization: Bearer <token>.
    Agar Marketapp X-API-Key ishlatsa, shu yerni o'zgartiring.
    """
    token = settings.marketapp_token
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def _base_url() -> str:
    return settings.marketapp_api_base.rstrip("/")


async def is_integration_reachable() -> bool:
    """
    Haqiqiy integratsiya mavjudligini TEKSHIRADI (yolg'on ko'rsatmaslik uchun).
    Yoqilmagan yoki token yo'q bo'lsa -> False.
    """
    if not (settings.marketapp_integration_enabled and settings.marketapp_api_base and settings.marketapp_token):
        return False
    try:
        async with httpx.AsyncClient(timeout=settings.marketapp_timeout_seconds) as client:
            resp = await client.get(_base_url(), headers=_headers())
            return resp.status_code < 500
    except Exception:
        return False


def _normalize_nft(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Marketapp javobidagi bitta NFT'ni loyihaning umumiy formatiga keltiradi.

    ⚠️ Maydon nomlari (id, name, image, price...) Swagger'dagi RentItem/RentedItem
    schemasiga qarab moslanishi kerak. Pastda keng tarqalgan nomlar bilan
    xavfsiz (fallback) o'qiymiz — aniq nomlar ma'lum bo'lganda soddalashtiriladi.
    """
    def pick(*keys, default=None):
        for k in keys:
            if k in raw and raw[k] is not None:
                return raw[k]
        return default

    return {
        "nft_ref": str(pick("id", "nft_id", "address", "ref", default="")),
        "name": str(pick("name", "title", default="NFT")),
        "image_url": str(pick("image", "image_url", "photo", "preview", default="")),
        "collection_name": pick("collection", "collection_name"),
        "daily_price_ton": float(pick("daily_price", "price_ton", "price", default=0) or 0),
        "allowed_durations": pick("durations", "rent_durations", default=[1, 3, 7, 30]),
        "is_available": bool(pick("available", "is_available", default=True)),
        "source": "marketapp",
        "raw": raw,
    }


async def fetch_rent_nfts(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """
    Marketapp'dan ijaraga mavjud NFT'lar ro'yxatini oladi va normalizatsiya qiladi.

    Integratsiya yoqilmagan bo'lsa NotImplementedError ko'taradi —
    chaqiruvchi tomon DEMO ma'lumotlarga qaytadi (yolg'on ko'rsatilmaydi).
    """
    if not (settings.marketapp_integration_enabled and settings.marketapp_api_base and settings.marketapp_token):
        raise NotImplementedError("Marketapp integratsiyasi yoqilmagan (demo rejim).")

    url = _base_url() + _EP["rent_nfts"]
    params = {"limit": limit, "offset": offset}
    async with httpx.AsyncClient(timeout=settings.marketapp_timeout_seconds) as client:
        resp = await client.get(url, headers=_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()

    # Javob strukturasi: ro'yxat yoki {items:[...]} / {nfts:[...]} / {results:[...]}
    items = data
    if isinstance(data, dict):
        for key in ("items", "nfts", "results", "data"):
            if isinstance(data.get(key), list):
                items = data[key]
                break
    if not isinstance(items, list):
        items = []

    return [_normalize_nft(it) for it in items if isinstance(it, dict)]


async def fetch_nft_detail(nft_ref: str) -> dict[str, Any] | None:
    """Bitta NFT tafsilotini oladi (integratsiya yoqilgan bo'lsa)."""
    if not (settings.marketapp_integration_enabled and settings.marketapp_api_base and settings.marketapp_token):
        raise NotImplementedError("Marketapp integratsiyasi yoqilmagan (demo rejim).")

    url = _base_url() + _EP["nft_detail"].format(id=nft_ref)
    async with httpx.AsyncClient(timeout=settings.marketapp_timeout_seconds) as client:
        resp = await client.get(url, headers=_headers())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _normalize_nft(resp.json())
