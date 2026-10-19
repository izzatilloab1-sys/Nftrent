"""
TON to'lov API — "auto to'lov" oqimi.

Xavfsizlik:
  - Foydalanuvchi faqat O'Z buyurtmasini to'laydi.
  - To'lov summasi SERVERdagi buyurtma qiymatidan olinadi (frontendга ishonilmaydi).
  - Idempotentlik: bir buyurtma ikki marta tasdiqlanmaydi.
  - Private key / seed ishlatilmaydi — faqat read-only tekshiruv.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.i18n import t
from app.models.order import OrderStatus, RentalOrder
from app.models.payment import PaymentAttempt, PaymentStatus
from app.models.user import User
from app.services import payment_settings_service
from app.services.ton_payment_service import (
    build_tonconnect_transaction,
    check_incoming_payment,
    payment_memo_for_order,
)

router = APIRouter(prefix="/api/payment", tags=["payment"])


@router.get("/config")
async def payment_config(db: AsyncSession = Depends(get_db)):
    """WebApp uchun to'lov sozlamasi (ochiq ma'lumot)."""
    ps = await payment_settings_service.get_settings(db)
    return {
        "payments_enabled": ps.payments_enabled,
        "receiving_address": ps.receiving_address,
        "tonconnect_manifest_url": ps.tonconnect_manifest_url,
    }


async def _get_own_order(db: AsyncSession, order_id: int, user: User) -> RentalOrder:
    res = await db.execute(select(RentalOrder).where(RentalOrder.id == order_id))
    order = res.scalar_one_or_none()
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail=t("err_not_found", user.language))
    return order


@router.post("/{order_id}/initiate")
async def initiate_payment(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    To'lovni boshlaydi: foydalanuvchi hamyonida imzolanadigan tranzaksiyani qaytaradi.
    """
    ps = await payment_settings_service.get_settings(db)
    if not ps.payments_enabled or not ps.receiving_address:
        raise HTTPException(status_code=400, detail=t("payment_later", user.language))

    order = await _get_own_order(db, order_id, user)
    if order.status in (OrderStatus.PAID, OrderStatus.RENTAL_ACTIVE, OrderStatus.RENTAL_COMPLETED):
        raise HTTPException(status_code=400, detail="Order already paid")

    memo = payment_memo_for_order(order.order_number)
    tx = build_tonconnect_transaction(
        receiving_address=ps.receiving_address,
        amount_ton=order.total_ton,   # SERVERdagi summa
        memo=memo,
    )

    # To'lov urinishini yozamiz (idempotency_key = memo)
    res = await db.execute(
        select(PaymentAttempt).where(PaymentAttempt.idempotency_key == memo)
    )
    if not res.scalar_one_or_none():
        db.add(PaymentAttempt(
            order_id=order.id, method="ton", status=PaymentStatus.INITIATED,
            idempotency_key=memo, amount_ton=order.total_ton,
        ))
        await db.flush()

    return {
        "transaction": tx,
        "amount_ton": order.total_ton,
        "memo": memo,
        "receiving_address": ps.receiving_address,
    }


@router.post("/{order_id}/verify")
async def verify_payment(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Blockchaindan to'lovni tekshiradi. Topilsa -> ijara AVTOMATIK faollashadi.
    WebApp buni bir necha marta chaqiradi (polling), yoki admin cron orqali.
    """
    ps = await payment_settings_service.get_settings(db)
    if not ps.payments_enabled or not ps.receiving_address:
        raise HTTPException(status_code=400, detail=t("payment_later", user.language))

    order = await _get_own_order(db, order_id, user)

    # Idempotentlik: allaqachon to'langan bo'lsa qaytaramiz
    if order.status in (OrderStatus.PAID, OrderStatus.RENTAL_ACTIVE, OrderStatus.RENTAL_COMPLETED):
        return {"confirmed": True, "status": order.status.value}

    memo = payment_memo_for_order(order.order_number)
    result = await check_incoming_payment(
        receiving_address=ps.receiving_address,
        expected_amount_ton=order.total_ton,
        memo=memo,
        testnet=(settings.env != "production"),
    )

    if not result.confirmed:
        return {"confirmed": False, "reason": result.reason}

    # --- To'lov tasdiqlandi: ijarani faollashtiramiz (bir marta) ---
    from datetime import datetime, timedelta, timezone

    res = await db.execute(
        select(PaymentAttempt).where(PaymentAttempt.idempotency_key == memo)
    )
    attempt = res.scalar_one_or_none()
    if attempt and attempt.status == PaymentStatus.CONFIRMED:
        return {"confirmed": True, "status": order.status.value}

    if attempt:
        attempt.status = PaymentStatus.CONFIRMED
        attempt.external_tx_hash = result.tx_hash

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.RENTAL_ACTIVE
    order.rental_start_at = now
    order.rental_end_at = now + timedelta(days=order.duration_days)
    await db.flush()

    return {
        "confirmed": True,
        "status": order.status.value,
        "tx_hash": result.tx_hash,
        "rental_end_at": order.rental_end_at.isoformat(),
    }
