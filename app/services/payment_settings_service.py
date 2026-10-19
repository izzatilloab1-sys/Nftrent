"""TON to'lov sozlamalarini boshqarish (faqat ochiq manzil)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import PaymentSetting


async def get_settings(db: AsyncSession) -> PaymentSetting:
    res = await db.execute(select(PaymentSetting).where(PaymentSetting.id == 1))
    row = res.scalar_one_or_none()
    if not row:
        row = PaymentSetting(id=1, receiving_address="", payments_enabled=False)
        db.add(row)
        await db.flush()
    return row


def _is_valid_ton_address(addr: str) -> bool:
    """
    Oddiy TON manzil tekshiruvi (to'liq EMAS, lekin aniq soxta qiymatni rad etadi).
    TON user-friendly manzil 48 belgili base64url (UQ.../EQ... bilan boshlanadi).
    """
    addr = (addr or "").strip()
    if len(addr) != 48:
        return False
    if not (addr.startswith("UQ") or addr.startswith("EQ") or addr.startswith("kQ") or addr.startswith("0Q")):
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    return all(c in allowed for c in addr)


async def update_settings(
    db: AsyncSession,
    *,
    receiving_address: str | None = None,
    tonconnect_manifest_url: str | None = None,
    payments_enabled: bool | None = None,
) -> PaymentSetting:
    row = await get_settings(db)

    if receiving_address is not None:
        addr = receiving_address.strip()
        if addr and not _is_valid_ton_address(addr):
            raise ValueError("invalid_ton_address")
        row.receiving_address = addr

    if tonconnect_manifest_url is not None:
        row.tonconnect_manifest_url = tonconnect_manifest_url.strip()

    if payments_enabled is not None:
        # To'lovni yoqishdan oldin manzil kiritilgan bo'lishi SHART
        if payments_enabled and not row.receiving_address:
            raise ValueError("address_required")
        row.payments_enabled = payments_enabled

    await db.flush()
    return row
