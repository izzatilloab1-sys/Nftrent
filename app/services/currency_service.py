"""TON/UZS kursini boshqarish — faqat admin o'zgartiradi."""
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.settings import CurrencySetting


async def get_current_rate(db: AsyncSession) -> float:
    """Joriy TON/UZS kursi. Yozuv bo'lmasa — .env dagi default."""
    res = await db.execute(
        select(CurrencySetting).order_by(desc(CurrencySetting.created_at)).limit(1)
    )
    row = res.scalar_one_or_none()
    if row:
        return row.ton_uzs_rate
    return settings.default_ton_uzs_rate


async def set_rate(db: AsyncSession, rate: float, admin_id: int | None) -> CurrencySetting:
    """Yangi kurs qo'shadi (tarix saqlanadi). rate musbat bo'lishi shart."""
    if rate is None or rate <= 0:
        raise ValueError("Kurs musbat son bo'lishi kerak")
    row = CurrencySetting(ton_uzs_rate=float(rate), changed_by_admin_id=admin_id)
    db.add(row)
    await db.flush()
    return row


async def get_rate_history(db: AsyncSession, limit: int = 50) -> list[CurrencySetting]:
    res = await db.execute(
        select(CurrencySetting).order_by(desc(CurrencySetting.created_at)).limit(limit)
    )
    return list(res.scalars().all())
