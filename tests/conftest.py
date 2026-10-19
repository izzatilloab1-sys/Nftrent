"""
Pytest umumiy sozlamalari va fixture'lar.

Eslatma: Integratsiya testlari (DB, API) SQLAlchemy/httpx/FastAPI talab qiladi.
Ular o'rnatilgan muhitda (pip install -r requirements.txt) to'liq ishlaydi.
"""
import asyncio
import os

import pytest

# Test muhiti uchun SQLite xotira bazasi
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("BOT_TOKEN", "123456789:TEST")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
