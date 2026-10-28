"""NFT katalogi va narx hisob-kitobi API."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.i18n import t
from app.models.nft import Nft, NftCollection
from app.schemas.schemas import NftDetailOut, NftOut, QuoteIn, QuoteOut
from app.services import currency_service, marketapp_adapter
from app.services.order_service import OrderError, parse_durations, quote_for_nft

router = APIRouter(prefix="/api/nfts", tags=["nfts"])


def _durations(nft: Nft) -> list[int]:
    try:
        return [int(x) for x in json.loads(nft.allowed_durations)]
    except Exception:
        return [1, 3, 7, 30]


async def _to_out(db: AsyncSession, nft: Nft, rate: float) -> NftOut:
    coll_name = nft.collection.name if nft.collection else None
    return NftOut(
        id=nft.id,
        nft_ref=nft.nft_ref,
        name=nft.name,
        image_url=nft.image_url,
        collection_name=coll_name,
        daily_price_ton=nft.daily_price_ton,
        daily_price_uzs=round(nft.daily_price_ton * rate),
        allowed_durations=_durations(nft),
        is_available=nft.is_available,
        is_popular=nft.is_popular,
        source=nft.source,
    )


def _live_to_out(item: dict, rate: float) -> NftOut:
    """Marketapp'dan normalizatsiya qilingan NFT dict'ini NftOut'ga aylantiradi.

    Live NFT'larning lokal DB id'si bo'lmaydi; id=0 va source='marketapp' bilan
    belgilaymiz. Ro'yxatda ko'rsatish uchun yetarli; tafsilot nft_ref orqali olinadi.
    """
    durations = item.get("allowed_durations") or [1, 3, 7, 30]
    try:
        durations = [int(x) for x in durations]
    except Exception:
        durations = [1, 3, 7, 30]
    daily = float(item.get("daily_price_ton") or 0)
    return NftOut(
        id=0,  # live NFT — lokal id yo'q
        nft_ref=str(item.get("nft_ref") or ""),
        name=str(item.get("name") or "NFT"),
        image_url=str(item.get("image_url") or "/static/img/placeholder.svg"),
        collection_name=item.get("collection_name"),
        daily_price_ton=daily,
        daily_price_uzs=round(daily * rate),
        allowed_durations=durations,
        is_available=bool(item.get("is_available", True)),
        is_popular=False,
        source="marketapp",
    )


@router.get("/integration-status")
async def integration_status():
    """Marketapp integratsiyasi holati — demo yoki live ekanini OCHIQ ko'rsatadi."""
    st = marketapp_adapter.get_integration_status()
    return {
        "enabled": st.enabled,
        "mode": st.mode,
        "message_uz": st.message_uz,
        "message_en": st.message_en,
    }


@router.get("", response_model=list[NftOut])
async def list_nfts(
    section: str = Query("all", pattern="^(all|popular|new)$"),
    q: str | None = None,
    sort: str = Query("default", pattern="^(default|price_asc|price_desc|newest)$"),
    duration: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Nft)
        .options(selectinload(Nft.collection))
        .where(Nft.is_hidden == False)  # noqa: E712
    )

    if section == "popular":
        stmt = stmt.where(Nft.is_popular == True)  # noqa: E712
    elif section == "new":
        stmt = stmt.order_by(Nft.created_at.desc())

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Nft.name.ilike(like), Nft.nft_ref.ilike(like)))

    if sort == "price_asc":
        stmt = stmt.order_by(Nft.daily_price_ton.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(Nft.daily_price_ton.desc())
    elif sort == "newest":
        stmt = stmt.order_by(Nft.created_at.desc())

    res = await db.execute(stmt)
    nfts = list(res.scalars().unique().all())

    # Muddat bo'yicha filtr (allowed_durations ichida bormi)
    if duration:
        nfts = [n for n in nfts if duration in _durations(n)]

    rate = await currency_service.get_current_rate(db)
    local = [await _to_out(db, n, rate) for n in nfts]

    # Marketapp integratsiyasi YOQILGAN bo'lsa — haqiqiy NFT'larni ham qo'shamiz.
    # O'CHIQ bo'lsa faqat demo (lokal) NFT'lar qaytadi (yolg'on "live" ko'rsatilmaydi).
    st = marketapp_adapter.get_integration_status()
    if st.enabled:
        try:
            live_raw = await marketapp_adapter.fetch_rent_nfts()
            live = [_live_to_out(item, rate) for item in live_raw]
            # Qidiruv/saralashni live natijalarga ham qo'llaymiz (oddiy)
            if q:
                ql = q.strip().lower()
                live = [x for x in live if ql in x.name.lower() or ql in x.nft_ref.lower()]
            if duration:
                live = [x for x in live if duration in x.allowed_durations]
            # Live NFT'lar birinchi ko'rsatiladi
            return live + local
        except NotImplementedError:
            pass
        except Exception:
            # Live xato bersa — demo bilan davom etamiz (ilova yiqilmaydi)
            pass

    return local


@router.get("/collections")
async def list_collections(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(NftCollection).order_by(NftCollection.name))
    cols = res.scalars().all()
    return [{"id": c.id, "name": c.name, "slug": c.slug, "description": c.description} for c in cols]


@router.get("/{nft_id}", response_model=NftDetailOut)
async def get_nft(nft_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Nft)
        .options(selectinload(Nft.collection))
        .where(Nft.id == nft_id, Nft.is_hidden == False)  # noqa: E712
    )
    nft = res.scalar_one_or_none()
    if not nft:
        raise HTTPException(status_code=404, detail=t("err_not_found"))
    rate = await currency_service.get_current_rate(db)
    base = await _to_out(db, nft, rate)
    return NftDetailOut(**base.model_dump(), description=None)


@router.post("/quote", response_model=QuoteOut)
async def quote(payload: QuoteIn, db: AsyncSession = Depends(get_db)):
    """
    Narx hisob-kitobi — SERVERDAGI kurs va komissiyalar bilan.
    Frontenddagi qiymatlarga ishonilmaydi.
    """
    res = await db.execute(select(Nft).where(Nft.id == payload.nft_id, Nft.is_hidden == False))  # noqa: E712
    nft = res.scalar_one_or_none()
    if not nft:
        raise HTTPException(status_code=404, detail=t("err_not_found"))
    try:
        q = await quote_for_nft(db, nft=nft, duration_days=payload.duration_days)
    except OrderError as e:
        raise HTTPException(status_code=400, detail=t(e.key))
    return QuoteOut(nft_id=nft.id, **q.to_dict())
