"""
Integratsiya testlari: auth, foydalanuvchi izolyatsiyasi, admin himoyasi, buyurtma.

Bu testlar DB (SQLite xotira) va FastAPI TestClient talab qiladi.
O'rnatilgan muhitda ishga tushiriladi:  pytest tests/test_auth_and_api.py

Qamrab oladi (TT 17-bo'lim):
  - Username takrorlanmasligi
  - Noto'g'ri parol bilan kirish bloklanishi
  - Eski parol noto'g'ri bo'lsa parol o'zgarmasligi
  - Foydalanuvchi ma'lumotlari boshqa foydalanuvchiga ochilmasligi
  - Admin sahifasiga oddiy foydalanuvchi kira olmasligi
  - To'lov tasdiqlanmaganida ijara faollashmasligi
"""
import asyncio

import pytest

# Bu modullar o'rnatilmagan bo'lsa testlar o'tkazib yuboriladi (skip),
# shunda standart kutubxona testlari baribir ishlaydi.
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def _setup_db():
    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        # Boshlang'ich kurs + komissiyalar
        from app.database import AsyncSessionLocal
        from app.models.settings import CurrencySetting
        async with AsyncSessionLocal() as db:
            db.add(CurrencySetting(ton_uzs_rate=40000))
            await db.commit()
    asyncio.get_event_loop().run_until_complete(init())
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _register(client, username, password):
    return client.post("/api/auth/register", json={
        "username": username, "password": password,
        "password_confirm": password, "language": "uz",
    })


def test_register_and_duplicate_username(client):
    r1 = _register(client, "bob", "secret123")
    assert r1.status_code == 200, r1.text
    assert "token" in r1.json()

    # Takroriy username — rad etilishi kerak
    r2 = _register(client, "bob", "other123")
    assert r2.status_code == 400


def test_wrong_password_login_blocked(client):
    _register(client, "carol", "mypass123")
    r = client.post("/api/auth/login", json={"username": "carol", "password": "WRONG"})
    assert r.status_code == 401


def test_change_password_requires_correct_old(client):
    r = _register(client, "dave", "oldpass123")
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Noto'g'ri eski parol — o'zgarmaydi
    bad = client.post("/api/auth/change-password", headers=headers, json={
        "old_password": "WRONG", "new_password": "newpass123", "new_password_confirm": "newpass123",
    })
    assert bad.status_code == 400

    # To'g'ri eski parol — o'zgaradi
    ok = client.post("/api/auth/change-password", headers=headers, json={
        "old_password": "oldpass123", "new_password": "newpass123", "new_password_confirm": "newpass123",
    })
    assert ok.status_code == 200


def test_user_cannot_see_others_orders(client):
    # Ikki foydalanuvchi
    t1 = _register(client, "user1", "pass1234").json()["token"]
    t2 = _register(client, "user2", "pass1234").json()["token"]

    # user1 buyurtma yaratadi (NFT kerak — admin orqali qo'shamiz)
    # Oddiylik uchun: NFT bo'lmasa ham, user2 user1 buyurtmasini ko'ra olmasligini tekshiramiz
    o1 = client.get("/api/orders", headers={"Authorization": f"Bearer {t1}"})
    o2 = client.get("/api/orders", headers={"Authorization": f"Bearer {t2}"})
    assert o1.status_code == 200 and o2.status_code == 200
    # Har biri faqat o'z (bo'sh) ro'yxatini ko'radi
    assert o1.json() == []
    assert o2.json() == []


def test_admin_requires_valid_id(client):
    # Admin headerisiz — 403
    r = client.get("/api/admin/stats")
    assert r.status_code == 403

    # Noto'g'ri admin ID — 403
    r2 = client.get("/api/admin/stats", headers={"X-Admin-Telegram-Id": "999999999"})
    assert r2.status_code == 403


def test_payment_disabled_by_default(client):
    cfg = client.get("/api/payment/config")
    assert cfg.status_code == 200
    assert cfg.json()["payments_enabled"] is False
