"""
Marketapp integratsiya ADAPTERI.

⚠️ OCHIQ OGOHLANTIRISH:
Hozirda Marketapp bilan rasmiy, ruxsat etilgan API integratsiyasi MAVJUD EMAS.
Shuning uchun bu adapter standart holatda DEMO rejimda ishlaydi va
ma'lumotlarни lokal bazadan (demo NFT'lar) qaytaradi.

Demo NFT'lar HAQIQIY, egalik qilish mumkin bo'lgan NFT'lar sifatida TAQDIM ETILMAYDI.

Haqiqiy integratsiya paydo bo'lganda:
  1. settings.marketapp_integration_enabled = true qiling
  2. MARKETAPP_API_BASE / MARKETAPP_API_KEY ni to'ldiring
  3. _fetch_from_marketapp() ni rasmiy API spetsifikatsiyasiga ko'ra to'ldiring
Hech qachon ishlaydigan deb YOLG'ON ko'rsatmang — bu interfeys shunga qarab loyihalangan.
"""
from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass
class IntegrationStatus:
    enabled: bool
    mode: str          # "demo" | "live"
    message_uz: str
    message_en: str


def get_integration_status() -> IntegrationStatus:
    if settings.marketapp_integration_enabled and settings.marketapp_api_base:
        return IntegrationStatus(
            enabled=True,
            mode="live",
            message_uz="Marketapp integratsiyasi yoqilgan.",
            message_en="Marketapp integration is enabled.",
        )
    return IntegrationStatus(
        enabled=False,
        mode="demo",
        message_uz=(
            "⚠️ Marketapp bilan rasmiy integratsiya hali mavjud emas. "
            "Ko'rsatilayotgan NFT'lar — demo (test) ma'lumotlari."
        ),
        message_en=(
            "⚠️ No official Marketapp integration yet. "
            "The NFTs shown are demo (test) data."
        ),
    )


async def is_integration_reachable() -> bool:
    """
    Haqiqiy integratsiya mavjudligini TEKSHIRADI (yolg'on ko'rsatmaslik uchun).
    enabled bo'lmasa — False. URL bo'lsa, haqiqatan ulanishni sinab ko'radi.
    """
    if not settings.marketapp_integration_enabled or not settings.marketapp_api_base:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(settings.marketapp_api_base)
            return resp.status_code < 500
    except Exception:
        return False


async def _fetch_from_marketapp() -> list[dict]:
    """
    Haqiqiy API chaqiruvi uchun joy. Rasmiy spetsifikatsiya kelganда to'ldiriladi.
    Hozircha hech narsa qaytarmaydi, chunki real integratsiya yo'q.
    """
    raise NotImplementedError(
        "Marketapp rasmiy API integratsiyasi hali amalga oshirilmagan."
    )
