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

# ---- Endpoint yo'llari (Marketapp Swagger'ga asoslangan) ----
# Base URL: https://marketapp.org  (barcha yo'llar /v1/ bilan boshlanadi).
# Schemalar: NFTsResponse, RentedNFTsResponse, PayRentNFTBody, RentCategory,
#            RentHistoryResponse, SortBy, HistoryOrderBy.
_EP = {
    # RentedNFTsResponse / NFTsResponse -> ijaraga mavjud NFT'lar
    "rented_nfts": "/v1/rent/nfts",
    # Bitta NFT tafsiloti
    "nft_detail": "/v1/rent/nfts/{id}",
    # RentCategory ro'yxati
    "rent_categories": "/v1/rent/categories",
    # RentHistoryResponse -> ijara tarixi (HistoryOrderBy parametri bilan)
    "rent_history": "/v1/rent/history",
    # PayRentNFTBody -> ijara to'lovi (to'lov yoqilganda ishlatiladi)
    "pay_rent": "/v1/rent/pay",
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


def _extract_items(data: Any) -> list[dict]:
    """
    Javobdan NFT ro'yxatini ajratadi.
    RentedNFTsResponse / NFTsResponse odatda {items:[...]} yoki {nfts:[...]}
    ko'rinishida bo'ladi; ro'yxat ham bo'lishi mumkin.
    """
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("items", "nfts", "results", "data", "rented", "list"):
            val = data.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
    return []


async def fetch_rent_nfts(
    limit: int = 100,
    offset: int = 0,
    category: str | None = None,
    sort_by: str | None = None,
) -> list[dict[str, Any]]:
    """
    Marketapp'dan ijaraga mavjud NFT'lar ro'yxatini oladi (RentedNFTsResponse).

    - category: ixtiyoriy RentCategory filtri.
    - sort_by: ixtiyoriy SortBy query parametri.
    - Integratsiya yoqilmagan bo'lsa NotImplementedError -> chaqiruvchi DEMO'ga qaytadi.
    """
    if not (settings.marketapp_integration_enabled and settings.marketapp_api_base and settings.marketapp_token):
        raise NotImplementedError("Marketapp integratsiyasi yoqilmagan (demo rejim).")

    url = _base_url() + _EP["rented_nfts"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if category:
        params["category"] = category    # RentCategory
    if sort_by:
        params["SortBy"] = sort_by        # SortBy (Swagger query param)

    async with httpx.AsyncClient(timeout=settings.marketapp_timeout_seconds) as client:
        resp = await client.get(url, headers=_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()

    return [_normalize_nft(it) for it in _extract_items(data)]


async def fetch_rent_history(
    limit: int = 50, offset: int = 0, order_by: str | None = None
) -> list[dict[str, Any]]:
    """
    Ijara tarixini oladi (RentHistoryResponse, HistoryOrderBy parametri bilan).
    """
    if not (settings.marketapp_integration_enabled and settings.marketapp_api_base and settings.marketapp_token):
        raise NotImplementedError("Marketapp integratsiyasi yoqilmagan (demo rejim).")

    url = _base_url() + _EP["rent_history"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if order_by:
        params["HistoryOrderBy"] = order_by   # HistoryOrderBy (Swagger query param)

    async with httpx.AsyncClient(timeout=settings.marketapp_timeout_seconds) as client:
        resp = await client.get(url, headers=_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
    return _extract_items(data)


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


async def fetch_rent_categories() -> list[str]:
    """RentCategory ro'yxatini oladi (integratsiya yoqilgan bo'lsa)."""
    if not (settings.marketapp_integration_enabled and settings.marketapp_api_base and settings.marketapp_token):
        raise NotImplementedError("Marketapp integratsiyasi yoqilmagan (demo rejim).")

    url = _base_url() + _EP["rent_categories"]
    async with httpx.AsyncClient(timeout=settings.marketapp_timeout_seconds) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, list):
        return [str(x) for x in data]
    if isinstance(data, dict):
        for key in ("categories", "items", "results"):
            if isinstance(data.get(key), list):
                return [str(x) for x in data[key]]
    return []


async def pay_rent(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Ijara to'lovini boshlaydi (PayRentNFTBody).

    ⚠️ To'lov oqimi loyihada standart holatda O'CHIQ. Bu funksiya faqat
    integratsiya + to'lov yoqilganda chaqiriladi. Hamyon maxfiy kaliti
    ishlatilmaydi — to'lovni foydalanuvchi o'z hamyonida tasdiqlaydi.
    """
    if not (settings.marketapp_integration_enabled and settings.marketapp_api_base and settings.marketapp_token):
        raise NotImplementedError("Marketapp integratsiyasi yoqilmagan (demo rejim).")

    url = _base_url() + _EP["pay_rent"]
    async with httpx.AsyncClient(timeout=settings.marketapp_timeout_seconds) as client:
        resp = await client.post(url, headers=_headers(), json=payload)
        resp.raise_for_status()
        return resp.json()
