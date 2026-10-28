"""Ijara buyurtmalari biznes-mantig'i."""
import json
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.nft import Nft
from app.models.order import OrderStatus, RentalItem, RentalOrder
from app.models.user import User
from app.services import commission_service, currency_service
from app.services.pricing import PriceQuote, compute_quote


class OrderError(Exception):
    def __init__(self, key: str):
        self.key = key
        super().__init__(key)


def _gen_order_number() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    rnd = secrets.token_hex(3).upper()
    return f"NR-{ts}-{rnd}"


def parse_durations(nft: Nft) -> list[int]:
    try:
        vals = json.loads(nft.allowed_durations)
        return [int(v) for v in vals if int(v) > 0]
    except Exception:
        return [1, 3, 7, 30]


async def quote_for_nft(
    db: AsyncSession, *, nft: Nft, duration_days: int
) -> PriceQuote:
    """NFT uchun narx hisob-kitobini (server kursi bilan) qaytaradi."""
    allowed = parse_durations(nft)
    if duration_days not in allowed:
        raise OrderError("err_invalid_duration")

    rate = await currency_service.get_current_rate(db)
    commissions = await commission_service.get_active_commissions(db)
    return compute_quote(
        daily_price_ton=nft.daily_price_ton,
        duration_days=duration_days,
        ton_uzs_rate=rate,
        commissions=commissions,
    )


async def create_draft_order(
    db: AsyncSession, *, user: User, nft_id: int, duration_days: int
) -> RentalOrder:
    """
    'Ijaraga olish' bosilganda DRAFT buyurtma yaratadi.
    ⚠️ Real to'lovga O'TMAYDI. Status PENDING_PAYMENT da qoladi.
    Narx, kurs va komissiyalar buyurtma vaqtida MUZLATILADI.
    """
    res = await db.execute(select(Nft).where(Nft.id == nft_id))
    nft = res.scalar_one_or_none()
    if not nft or nft.is_hidden:
        raise OrderError("err_not_found")
    if not nft.is_available:
        raise OrderError("err_nft_unavailable")

    quote = await quote_for_nft(db, nft=nft, duration_days=duration_days)

    order = RentalOrder(
        order_number=_gen_order_number(),
        user_id=user.id,
        status=OrderStatus.PENDING_PAYMENT,  # to'lov kutilmoqda; real to'lov hali yo'q
        ton_uzs_rate=quote.ton_uzs_rate,
        base_price_ton=quote.base_price_ton,
        commission_ton=quote.commission_ton,
        network_fee_ton=quote.network_fee_ton,
        service_fee_ton=quote.service_fee_ton,
        refundable_deposit_ton=quote.refundable_deposit_ton,
        total_ton=quote.total_ton,
        base_price_uzs=quote.base_price_uzs,
        total_uzs=quote.total_uzs,
        commission_breakdown=json.dumps(
            [ln.__dict__ for ln in quote.lines], ensure_ascii=False
        ),
        duration_days=duration_days,
    )
    db.add(order)
    await db.flush()

    item = RentalItem(
        order_id=order.id,
        nft_id=nft.id,
        nft_ref=nft.nft_ref,
        nft_name=nft.name,
        nft_image_url=nft.image_url,
        daily_price_ton=nft.daily_price_ton,
    )
    db.add(item)
    await db.flush()
    return order


async def list_user_orders(db: AsyncSession, *, user_id: int) -> list[RentalOrder]:
    res = await db.execute(
        select(RentalOrder)
        .options(selectinload(RentalOrder.items))
        .where(RentalOrder.user_id == user_id)
        .order_by(RentalOrder.created_at.desc())
    )
    return list(res.scalars().unique().all())


async def get_order_with_items(db: AsyncSession, *, order_id: int) -> RentalOrder | None:
    res = await db.execute(
        select(RentalOrder)
        .options(selectinload(RentalOrder.items))
        .where(RentalOrder.id == order_id)
    )
    return res.scalar_one_or_none()


async def refresh_completed_rentals(db: AsyncSession, *, user_id: int) -> None:
    """
    Ijara tugash vaqti o'tgan FAOL ijaralarni 'rental_completed' ga o'tkazadi.
    Haqiqiy on-chain tugatish faqat integratsiya orqali bo'ladi — bu lokal holat.
    """
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(RentalOrder).where(
            RentalOrder.user_id == user_id,
            RentalOrder.status == OrderStatus.RENTAL_ACTIVE,
        )
    )
    for order in res.scalars().all():
        end = order.rental_end_at
        if end is None:
            continue
        # SQLite naive datetime qaytarishi mumkin -> UTC deb hisoblaymiz
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end <= now:
            order.status = OrderStatus.RENTAL_COMPLETED
    await db.flush()
