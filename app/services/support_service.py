"""Support username'ni boshqarish — bitta yozuv (id=1)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.settings import SupportSetting


async def get_support_username(db: AsyncSession) -> str:
    res = await db.execute(select(SupportSetting).where(SupportSetting.id == 1))
    row = res.scalar_one_or_none()
    if row:
        return row.support_username
    return settings.default_support_username


async def set_support_username(db: AsyncSession, username: str) -> str:
    username = username.lstrip("@").strip()
    res = await db.execute(select(SupportSetting).where(SupportSetting.id == 1))
    row = res.scalar_one_or_none()
    if row:
        row.support_username = username
    else:
        row = SupportSetting(id=1, support_username=username)
        db.add(row)
    await db.flush()
    return username
