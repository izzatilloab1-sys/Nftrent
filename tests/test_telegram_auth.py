"""
Telegram initData HMAC tekshiruvi testlari.

Faqat standart kutubxona (hashlib/hmac) ga bog'liq — har qanday muhitda ishlaydi.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.telegram_auth import TelegramAuthError, validate_init_data

TEST_TOKEN = "123456789:TEST"


def _make_init_data(token: str, user: dict, auth_date: int | None = None) -> str:
    """Haqiqiy Telegram imzosi bilan to'g'ri initData yasaydi."""
    auth_date = auth_date or int(time.time())
    fields = {
        "auth_date": str(auth_date),
        "query_id": "AAEtest",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    fields["hash"] = h
    return urlencode(fields)


def test_valid_init_data(monkeypatch):
    from app.core import telegram_auth
    monkeypatch.setattr(telegram_auth.settings, "bot_token", TEST_TOKEN)
    user = {"id": 555, "username": "alice", "language_code": "uz"}
    init = _make_init_data(TEST_TOKEN, user)
    result = validate_init_data(init)
    assert result["telegram_id"] == 555
    assert result["username"] == "alice"


def test_tampered_hash_rejected(monkeypatch):
    from app.core import telegram_auth
    monkeypatch.setattr(telegram_auth.settings, "bot_token", TEST_TOKEN)
    user = {"id": 555, "username": "alice"}
    init = _make_init_data(TEST_TOKEN, user)
    # hash'ni buzamiz
    tampered = init.replace("hash=", "hash=0000")
    with pytest.raises(TelegramAuthError):
        validate_init_data(tampered)


def test_wrong_token_rejected(monkeypatch):
    from app.core import telegram_auth
    monkeypatch.setattr(telegram_auth.settings, "bot_token", TEST_TOKEN)
    user = {"id": 555}
    # BOSHQA token bilan imzolangan initData — rad etilishi kerak
    init = _make_init_data("999:OTHER", user)
    with pytest.raises(TelegramAuthError):
        validate_init_data(init)


def test_expired_init_data(monkeypatch):
    from app.core import telegram_auth
    monkeypatch.setattr(telegram_auth.settings, "bot_token", TEST_TOKEN)
    user = {"id": 555}
    old = int(time.time()) - 100000
    init = _make_init_data(TEST_TOKEN, user, auth_date=old)
    with pytest.raises(TelegramAuthError):
        validate_init_data(init, max_age=3600)


def test_empty_init_data(monkeypatch):
    from app.core import telegram_auth
    monkeypatch.setattr(telegram_auth.settings, "bot_token", TEST_TOKEN)
    with pytest.raises(TelegramAuthError):
        validate_init_data("")
