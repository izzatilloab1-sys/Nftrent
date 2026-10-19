"""Komissiya sozlamalarini boshqarish."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import CommissionSetting


async def get_active_commissions(db: AsyncSession) -> list[CommissionSetting]:
    res = await db.execute(
        select(CommissionSetting)
        .where(CommissionSetting.is_active == True)  # noqa: E712
        .order_by(CommissionSetting.order_index)
    )
    return list(res.scalars().all())


async def get_all_commissions(db: AsyncSession) -> list[CommissionSetting]:
    res = await db.execute(
        select(CommissionSetting).order_by(CommissionSetting.order_index)
    )
    return list(res.scalars().all())
