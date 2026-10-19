"""Ijara buyurtmalari API — foydalanuvchi faqat O'Z buyurtmalarini ko'radi."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.i18n import t
from app.models.order import RentalOrder
from app.models.user import User
from app.schemas.schemas import CreateOrderIn, OrderOut
from app.services import order_service
from app.services.order_service import OrderError

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _order_to_out(order: RentalOrder, lang: str) -> OrderOut:
    nft_name = order.items[0].nft_name if order.items else None
    nft_img = order.items[0].nft_image_url if order.items else None
    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        status=order.status.value,
        duration_days=order.duration_days,
        base_price_ton=order.base_price_ton,
        total_ton=order.total_ton,
        base_price_uzs=order.base_price_uzs,
        total_uzs=order.total_uzs,
        ton_uzs_rate=order.ton_uzs_rate,
        rental_start_at=order.rental_start_at,
        rental_end_at=order.rental_end_at,
        created_at=order.created_at,
        nft_name=nft_name,
        nft_image_url=nft_img,
        payment_note=t("payment_later", lang),
    )


@router.post("", response_model=OrderOut)
async def create_order(
    payload: CreateOrderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    'Ijaraga olish' — DRAFT/PENDING buyurtma yaratadi.
    ⚠️ Real to'lovga o'tmaydi. To'lov keyingi bosqichda ulanadi.
    """
    try:
        order = await order_service.create_draft_order(
            db, user=user, nft_id=payload.nft_id, duration_days=payload.duration_days
        )
    except OrderError as e:
        raise HTTPException(status_code=400, detail=t(e.key, user.language))

    # items ni eager-load bilan qayta o'qiymiz (async lazy-load oldini olish)
    order = await order_service.get_order_with_items(db, order_id=order.id)
    return _order_to_out(order, user.language)


@router.get("", response_model=list[OrderOut])
async def my_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Tugagan ijaralarni yangilash
    await order_service.refresh_completed_rentals(db, user_id=user.id)
    orders = await order_service.list_user_orders(db, user_id=user.id)
    return [_order_to_out(o, user.language) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.get_order_with_items(db, order_id=order_id)
    # Foydalanuvchi faqat O'Z buyurtmasini ko'radi
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail=t("err_not_found", user.language))
    return _order_to_out(order, user.language)
