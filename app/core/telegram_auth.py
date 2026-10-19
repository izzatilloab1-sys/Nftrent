"""
Telegram WebApp `initData` ni server tomonida tekshirish.

Rasmiy algoritm (Telegram hujjatlari):
  secret_key = HMAC_SHA256(key="WebAppData", data=bot_token)
  computed_hash = HMAC_SHA256(key=secret_key, data=data_check_string)
  computed_hash == hash  -> ma'lumot haqiqiy
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.config import settings

# initData maksimal yoshi (soniya) — eski ma'lumotni rad etish
MAX_AUTH_AGE_SECONDS = 24 * 3600


class TelegramAuthError(Exception):
    pass


def validate_init_data(init_data: str, max_age: int = MAX_AUTH_AGE_SECONDS) -> dict:
    """
    initData (query-string) ni tekshiradi va foydalanuvchi ma'lumotini qaytaradi.
    Xato bo'lsa TelegramAuthError ko'taradi.
    """
    if not init_data:
        raise TelegramAuthError("initData bo'sh")

    if not settings.bot_token:
        raise TelegramAuthError("BOT_TOKEN sozlanmagan")

    # parse_qsl tartibni saqlaydi; dict ga o'tkazamiz
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("hash topilmadi")

    # data_check_string: kalitlar alifbo tartibida, key=value, \n bilan
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    secret_key = hmac.new(
        b"WebAppData", settings.bot_token.encode(), hashlib.sha256
    ).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise TelegramAuthError("initData imzosi noto'g'ri")

    # Yoshni tekshirish
    auth_date = parsed.get("auth_date")
    if auth_date and auth_date.isdigit():
        if time.time() - int(auth_date) > max_age:
            raise TelegramAuthError("initData muddati o'tgan")

    # Foydalanuvchi JSON
    user_raw = parsed.get("user")
    user = {}
    if user_raw:
        try:
            user = json.loads(user_raw)
        except json.JSONDecodeError:
            raise TelegramAuthError("user JSON buzuq")

    return {
        "user": user,
        "telegram_id": user.get("id"),
        "username": user.get("username"),
        "language_code": user.get("language_code"),
        "auth_date": auth_date,
        "raw": parsed,
    }
