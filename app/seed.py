"""
Demo ma'lumotlarni yuklash + DB jadvallarini yaratish.

⚠️ Bu DEMO (test) NFT'lar. Haqiqiy, egalik qilish mumkin bo'lgan NFT'lar EMAS.
Marketapp bilan rasmiy integratsiya bo'lmaguncha shunday qoladi.

Ishga tushirish:  python -m app.seed
"""
import asyncio
import json

from sqlalchemy import func, select

from app.config import settings
from app.database import AsyncSessionLocal, Base, engine
from app.models.nft import Nft, NftCollection
from app.models.settings import (
    CommissionKind,
    CommissionSetting,
    CommissionType,
    CurrencySetting,
    PaymentSetting,
    SupportSetting,
)

# Demo to'plamlar
DEMO_COLLECTIONS = [
    {"name": "Telegram Classic Gifts", "slug": "tg-classic", "description": "Klassik Telegram sovg'alari"},
    {"name": "Premium Collectibles", "slug": "premium", "description": "Premium kolleksiya"},
    {"name": "Rare Drops", "slug": "rare-drops", "description": "Noyob to'plam"},
]

# Demo NFT'lar (barchasi source="demo")
DEMO_NFTS = [
    {"nft_ref": "GIFT-1001", "name": "Golden Star", "collection": "tg-classic",
     "daily_price_ton": 0.5, "popular": True, "img": "star-gold"},
    {"nft_ref": "GIFT-1002", "name": "Diamond Ring", "collection": "premium",
     "daily_price_ton": 1.2, "popular": True, "img": "diamond-ring"},
    {"nft_ref": "GIFT-1003", "name": "Blue Rocket", "collection": "tg-classic",
     "daily_price_ton": 0.35, "popular": False, "img": "rocket-blue"},
    {"nft_ref": "GIFT-1004", "name": "Lucky Clover", "collection": "rare-drops",
     "daily_price_ton": 0.8, "popular": True, "img": "clover"},
    {"nft_ref": "GIFT-1005", "name": "Crystal Heart", "collection": "premium",
     "daily_price_ton": 1.5, "popular": False, "img": "heart-crystal"},
    {"nft_ref": "GIFT-1006", "name": "Fire Phoenix", "collection": "rare-drops",
     "daily_price_ton": 2.0, "popular": True, "img": "phoenix"},
    {"nft_ref": "GIFT-1007", "name": "Silver Crown", "collection": "premium",
     "daily_price_ton": 1.0, "popular": False, "img": "crown-silver"},
    {"nft_ref": "GIFT-1008", "name": "Magic Gem", "collection": "tg-classic",
     "daily_price_ton": 0.6, "popular": False, "img": "gem-purple"},
]

# Demo komissiyalar (admin keyin o'zgartiradi) — qiymatlar taxminiy, haqiqiy deb qabul qilinmaydi
DEMO_COMMISSIONS = [
    {"kind": CommissionKind.MARKETPLACE, "calc_type": CommissionType.PERCENT, "value": 5.0,
     "order_index": 1, "label_uz": "Marketplace komissiyasi", "label_en": "Marketplace fee"},
    {"kind": CommissionKind.NETWORK, "calc_type": CommissionType.FLAT_TON, "value": 0.05,
     "order_index": 2, "label_uz": "TON tarmoq xarajati", "label_en": "TON network fee"},
    {"kind": CommissionKind.SERVICE, "calc_type": CommissionType.PERCENT, "value": 2.0,
     "order_index": 3, "label_uz": "Xizmat haqi", "label_en": "Service fee"},
    {"kind": CommissionKind.REFUNDABLE_DEPOSIT, "calc_type": CommissionType.PERCENT, "value": 10.0,
     "order_index": 4, "label_uz": "Qaytariladigan depozit", "label_en": "Refundable deposit"},
]


def placeholder_image(name: str) -> str:
    """Demo rasm uchun SVG placeholder (data URL) — tashqi so'rov kerak emas."""
    return f"/static/img/{name}.svg"


async def seed():
    # Jadvallarni yaratish (dev; prod'da alembic ishlatiladi)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # To'plamlar
        existing = (await db.execute(select(func.count(NftCollection.id)))).scalar_one()
        coll_map: dict[str, int] = {}
        if existing == 0:
            for c in DEMO_COLLECTIONS:
                col = NftCollection(name=c["name"], slug=c["slug"], description=c["description"])
                db.add(col)
                await db.flush()
                coll_map[c["slug"]] = col.id
        else:
            res = await db.execute(select(NftCollection))
            for col in res.scalars().all():
                coll_map[col.slug] = col.id

        # NFT'lar
        nft_count = (await db.execute(select(func.count(Nft.id)))).scalar_one()
        if nft_count == 0:
            for n in DEMO_NFTS:
                db.add(Nft(
                    nft_ref=n["nft_ref"],
                    name=n["name"],
                    image_url=placeholder_image(n["img"]),
                    collection_id=coll_map.get(n["collection"]),
                    daily_price_ton=n["daily_price_ton"],
                    allowed_durations=json.dumps([1, 3, 7, 30]),
                    is_available=True,
                    is_hidden=False,
                    is_popular=n["popular"],
                    source="demo",
                ))

        # Komissiyalar
        comm_count = (await db.execute(select(func.count(CommissionSetting.id)))).scalar_one()
        if comm_count == 0:
            for c in DEMO_COMMISSIONS:
                db.add(CommissionSetting(
                    kind=c["kind"], calc_type=c["calc_type"], value=c["value"],
                    order_index=c["order_index"], is_active=True,
                    label_uz=c["label_uz"], label_en=c["label_en"],
                ))

        # Boshlang'ich kurs
        rate_count = (await db.execute(select(func.count(CurrencySetting.id)))).scalar_one()
        if rate_count == 0:
            db.add(CurrencySetting(ton_uzs_rate=settings.default_ton_uzs_rate, changed_by_admin_id=None))

        # Support
        res = await db.execute(select(SupportSetting).where(SupportSetting.id == 1))
        if not res.scalar_one_or_none():
            db.add(SupportSetting(id=1, support_username=settings.default_support_username))

        # To'lov sozlamalari (boshida o'chiq — admin manzil kiritib yoqadi)
        res = await db.execute(select(PaymentSetting).where(PaymentSetting.id == 1))
        if not res.scalar_one_or_none():
            db.add(PaymentSetting(id=1, receiving_address="", payments_enabled=False))

        await db.commit()
    print("✅ Demo ma'lumotlar yuklandi (NFT'lar — DEMO/test, haqiqiy emas).")


if __name__ == "__main__":
    asyncio.run(seed())
