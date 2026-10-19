"""Admin panel API — faqat server tomonida tasdiqlangan adminlar."""
import json
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database import get_db
from app.i18n import t
from app.models.nft import Nft
from app.models.order import OrderStatus, RentalOrder
from app.models.settings import (
    CommissionKind,
    CommissionSetting,
    CommissionType,
)
from app.models.user import User
from app.schemas.schemas import (
    CommissionIn,
    NftAdminIn,
    PaymentSettingsIn,
    RateIn,
    SupportIn,
)
from app.services import (
    audit_service,
    commission_service,
    currency_service,
    payment_settings_service,
    support_service,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------- Statistika ----------------
@router.get("/stats")
async def stats(admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    users_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    orders_count = (await db.execute(select(func.count(RentalOrder.id)))).scalar_one()
    active_rentals = (
        await db.execute(
            select(func.count(RentalOrder.id)).where(
                RentalOrder.status == OrderStatus.RENTAL_ACTIVE
            )
        )
    ).scalar_one()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = (
        await db.execute(
            select(func.count(RentalOrder.id)).where(RentalOrder.created_at >= today_start)
        )
    ).scalar_one()
    rate = await currency_service.get_current_rate(db)
    return {
        "users_count": users_count,
        "orders_count": orders_count,
        "active_rentals": active_rentals,
        "today_orders": today_orders,
        "current_ton_rate": rate,
        "payments_mode": "demo",  # to'lovlar hozircha demo
    }


# ---------------- TON kursi ----------------
@router.get("/rate")
async def get_rate(admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rate = await currency_service.get_current_rate(db)
    history = await currency_service.get_rate_history(db, limit=50)
    return {
        "current": rate,
        "history": [
            {
                "rate": h.ton_uzs_rate,
                "changed_by": h.changed_by_admin_id,
                "created_at": h.created_at.isoformat(),
            }
            for h in history
        ],
    }


@router.post("/rate")
async def set_rate(
    payload: RateIn, admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    try:
        row = await currency_service.set_rate(db, payload.rate, admin_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=t("err_rate_positive"))
    await audit_service.log_action(
        db, admin_telegram_id=admin_id, action="set_ton_rate",
        entity="currency", entity_id=str(row.id), details={"rate": payload.rate},
    )
    return {"ok": True, "current": row.ton_uzs_rate}


# ---------------- NFT boshqaruvi ----------------
@router.get("/nfts")
async def admin_nfts(admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Nft).order_by(Nft.id.desc()))
    nfts = res.scalars().all()
    return [
        {
            "id": n.id, "nft_ref": n.nft_ref, "name": n.name, "image_url": n.image_url,
            "collection_id": n.collection_id, "daily_price_ton": n.daily_price_ton,
            "allowed_durations": json.loads(n.allowed_durations),
            "is_available": n.is_available, "is_hidden": n.is_hidden,
            "is_popular": n.is_popular, "source": n.source,
        }
        for n in nfts
    ]


@router.post("/nfts")
async def create_nft(
    payload: NftAdminIn, admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    nft = Nft(
        nft_ref=payload.nft_ref,
        name=payload.name,
        image_url=payload.image_url,
        collection_id=payload.collection_id,
        daily_price_ton=payload.daily_price_ton,
        allowed_durations=json.dumps(payload.allowed_durations),
        is_available=payload.is_available,
        is_hidden=payload.is_hidden,
        is_popular=payload.is_popular,
        source="demo",
    )
    db.add(nft)
    await db.flush()
    await audit_service.log_action(
        db, admin_telegram_id=admin_id, action="create_nft", entity="nft", entity_id=str(nft.id)
    )
    return {"ok": True, "id": nft.id}


@router.put("/nfts/{nft_id}")
async def update_nft(
    nft_id: int, payload: NftAdminIn,
    admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Nft).where(Nft.id == nft_id))
    nft = res.scalar_one_or_none()
    if not nft:
        raise HTTPException(status_code=404, detail=t("err_not_found"))
    nft.nft_ref = payload.nft_ref
    nft.name = payload.name
    nft.image_url = payload.image_url
    nft.collection_id = payload.collection_id
    nft.daily_price_ton = payload.daily_price_ton
    nft.allowed_durations = json.dumps(payload.allowed_durations)
    nft.is_available = payload.is_available
    nft.is_hidden = payload.is_hidden
    nft.is_popular = payload.is_popular
    await db.flush()
    await audit_service.log_action(
        db, admin_telegram_id=admin_id, action="update_nft", entity="nft", entity_id=str(nft.id)
    )
    return {"ok": True}


@router.post("/nfts/{nft_id}/toggle")
async def toggle_nft(
    nft_id: int, admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Nft).where(Nft.id == nft_id))
    nft = res.scalar_one_or_none()
    if not nft:
        raise HTTPException(status_code=404, detail=t("err_not_found"))
    nft.is_hidden = not nft.is_hidden
    await db.flush()
    await audit_service.log_action(
        db, admin_telegram_id=admin_id, action="toggle_nft", entity="nft",
        entity_id=str(nft.id), details={"is_hidden": nft.is_hidden},
    )
    return {"ok": True, "is_hidden": nft.is_hidden}


# ---------------- Komissiyalar ----------------
@router.get("/commissions")
async def get_commissions(admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    comms = await commission_service.get_all_commissions(db)
    return [
        {
            "id": c.id, "kind": c.kind.value, "calc_type": c.calc_type.value,
            "value": c.value, "order_index": c.order_index, "is_active": c.is_active,
            "label_uz": c.label_uz, "label_en": c.label_en,
        }
        for c in comms
    ]


@router.put("/commissions/{commission_id}")
async def update_commission(
    commission_id: int, payload: CommissionIn,
    admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(CommissionSetting).where(CommissionSetting.id == commission_id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail=t("err_not_found"))
    try:
        c.kind = CommissionKind(payload.kind)
        c.calc_type = CommissionType(payload.calc_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid kind/calc_type")
    c.value = payload.value
    c.order_index = payload.order_index
    c.is_active = payload.is_active
    c.label_uz = payload.label_uz
    c.label_en = payload.label_en
    await db.flush()
    await audit_service.log_action(
        db, admin_telegram_id=admin_id, action="update_commission",
        entity="commission", entity_id=str(c.id),
    )
    return {"ok": True}


# ---------------- Foydalanuvchilar ----------------
@router.get("/users")
async def admin_users(
    q: str | None = None,
    admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        stmt = stmt.where(User.username.ilike(f"%{q.strip()}%"))
    res = await db.execute(stmt)
    users = res.scalars().all()
    out = []
    for u in users:
        cnt = (
            await db.execute(
                select(func.count(RentalOrder.id)).where(RentalOrder.user_id == u.id)
            )
        ).scalar_one()
        out.append({
            "id": u.id, "username": u.username, "language": u.language,
            "created_at": u.created_at.isoformat(), "is_blocked": u.is_blocked,
            "orders_count": cnt,
            # ⚠️ Parol hech qachon qaytarilmaydi
        })
    return out


@router.post("/users/{user_id}/block")
async def toggle_block_user(
    user_id: int, admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(User).where(User.id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail=t("err_not_found"))
    u.is_blocked = not u.is_blocked
    await db.flush()
    await audit_service.log_action(
        db, admin_telegram_id=admin_id, action="toggle_block_user",
        entity="user", entity_id=str(u.id), details={"is_blocked": u.is_blocked},
    )
    return {"ok": True, "is_blocked": u.is_blocked}


@router.get("/users/{user_id}/orders")
async def admin_user_orders(
    user_id: int, admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(RentalOrder).where(RentalOrder.user_id == user_id).order_by(RentalOrder.created_at.desc())
    )
    orders = res.scalars().unique().all()
    return [
        {
            "id": o.id, "order_number": o.order_number, "status": o.status.value,
            "total_ton": o.total_ton, "total_uzs": o.total_uzs,
            "created_at": o.created_at.isoformat(),
        }
        for o in orders
    ]


# ---------------- Support ----------------
@router.get("/support")
async def get_support(admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return {"support_username": await support_service.get_support_username(db)}


@router.post("/support")
async def set_support(
    payload: SupportIn, admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    username = await support_service.set_support_username(db, payload.support_username)
    await audit_service.log_action(
        db, admin_telegram_id=admin_id, action="set_support",
        entity="support", details={"username": username},
    )
    return {"ok": True, "support_username": username}


# ---------------- TON to'lov sozlamalari ----------------
@router.get("/payment-settings")
async def get_payment_settings(
    admin_id: int = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    ps = await payment_settings_service.get_settings(db)
    return {
        "receiving_address": ps.receiving_address,
        "tonconnect_manifest_url": ps.tonconnect_manifest_url,
        "payments_enabled": ps.payments_enabled,
    }


@router.post("/payment-settings")
async def set_payment_settings(
    payload: PaymentSettingsIn,
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    TON qabul qiluvchi manzilini va to'lov yoqilganlik holatini o'zgartiradi.
    ⚠️ Faqat OCHIQ manzil. Seed/private key QABUL QILINMAYDI.
    """
    try:
        ps = await payment_settings_service.update_settings(
            db,
            receiving_address=payload.receiving_address,
            tonconnect_manifest_url=payload.tonconnect_manifest_url,
            payments_enabled=payload.payments_enabled,
        )
    except ValueError as e:
        msg = {
            "invalid_ton_address": "TON manzili noto'g'ri (UQ.../EQ... bilan 48 belgi).",
            "address_required": "Avval qabul qiluvchi manzilni kiriting.",
        }.get(str(e), "Xatolik")
        raise HTTPException(status_code=400, detail=msg)

    await audit_service.log_action(
        db, admin_telegram_id=admin_id, action="set_payment_settings",
        entity="payment_settings",
        details={"address": ps.receiving_address, "enabled": ps.payments_enabled},
    )
    return {
        "ok": True,
        "receiving_address": ps.receiving_address,
        "payments_enabled": ps.payments_enabled,
    }
