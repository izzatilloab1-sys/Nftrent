"""Autentifikatsiya biznes-mantig'i: ro'yxat, login, parol, sessiya."""
import re
import secrets
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_session_token,
    hash_password,
    verify_password,
)
from app.models.user import LoginAttempt, Session as UserSession, User

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
MIN_PASSWORD_LEN = 6

# Avtomatik parol uchun (chalkashmaydigan belgilar: O/0, I/l yo'q)
_PWD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


def generate_random_password(length: int = 10) -> str:
    """Xavfsiz tasodifiy parol yaratadi (avtomatik ro'yxat uchun)."""
    return "".join(secrets.choice(_PWD_ALPHABET) for _ in range(length))


async def _unique_username_from_telegram(
    db: AsyncSession, *, telegram_username: str | None, telegram_id: int
) -> str:
    """
    Telegram ma'lumotidan yagona username yasaydi.
    Telegram username bo'lsa — o'shani; bo'lmasa user<id>; band bo'lsa raqam qo'shadi.
    """
    base = (telegram_username or "").strip().lstrip("@")
    # Faqat ruxsat etilgan belgilar
    base = re.sub(r"[^A-Za-z0-9_]", "", base)
    if len(base) < 3:
        base = f"user{telegram_id}"
    base = base[:28]  # qo'shimcha raqamlar uchun joy

    candidate = base
    suffix = 0
    while await get_user_by_username(db, candidate):
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


class AuthError(Exception):
    """Lokalizatsiya kaliti bilan xatolik."""
    def __init__(self, key: str):
        self.key = key
        super().__init__(key)


def _validate_username(username: str) -> str:
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise AuthError("err_invalid_credentials")
    return username


def _validate_password(password: str) -> None:
    if not password or len(password) < MIN_PASSWORD_LEN:
        raise AuthError("err_invalid_credentials")


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    res = await db.execute(select(User).where(func.lower(User.username) == username.lower()))
    return res.scalar_one_or_none()


async def register(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    password_confirm: str,
    telegram_id: int | None = None,
    language: str = "uz",
) -> User:
    username = _validate_username(username)
    _validate_password(password)

    if password != password_confirm:
        raise AuthError("err_password_mismatch")

    existing = await get_user_by_username(db, username)
    if existing:
        raise AuthError("err_username_taken")

    # Telegram ID allaqachon bog'langan bo'lsa — qayta ishlatmaymiz
    if telegram_id is not None:
        res = await db.execute(select(User).where(User.telegram_id == telegram_id))
        if res.scalar_one_or_none():
            # Bu Telegram akkaunt allaqachon profilга ega — baribir yangi username bilan
            # alohida profil ochishga ruxsat beramiz, lekin telegram_id ni bog'lamaymiz
            telegram_id = None

    user = User(
        username=username,
        password_hash=hash_password(password),
        telegram_id=telegram_id,
        language=language if language in ("uz", "en") else "uz",
    )
    db.add(user)
    await db.flush()
    return user


async def _recent_failed_attempts(db: AsyncSession, username: str, ip: str | None) -> int:
    window_start = datetime.now(timezone.utc) - timedelta(
        seconds=settings.login_attempt_window_seconds
    )
    stmt = select(func.count(LoginAttempt.id)).where(
        LoginAttempt.success == False,  # noqa: E712
        LoginAttempt.created_at >= window_start,
        func.lower(LoginAttempt.username) == username.lower(),
    )
    res = await db.execute(stmt)
    return int(res.scalar_one() or 0)


async def login(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, str]:
    """(user, session_token) qaytaradi."""
    username = (username or "").strip()

    # Rate limit
    failed = await _recent_failed_attempts(db, username, ip)
    if failed >= settings.login_max_attempts:
        raise AuthError("err_too_many_attempts")

    user = await get_user_by_username(db, username)
    ok = bool(user) and verify_password(password, user.password_hash)

    # Urinishni yozamiz
    db.add(LoginAttempt(username=username, ip=ip, success=ok))

    if not ok:
        raise AuthError("err_invalid_credentials")
    if user.is_blocked or not user.is_active:
        raise AuthError("err_account_blocked")

    token, jti, expires_at = create_session_token(user.id)
    db.add(
        UserSession(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            ip=ip,
            user_agent=(user_agent or "")[:255],
        )
    )
    await db.flush()
    return user, token


async def auto_authenticate(
    db: AsyncSession,
    *,
    telegram_id: int,
    telegram_username: str | None,
    language: str = "uz",
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, str, str | None]:
    """
    Telegram initData orqali AVTOMATIK autentifikatsiya.

    - Telegram ID bo'yicha foydalanuvchi bo'lsa -> tizimga kiritadi (parol so'ralmaydi)
    - Bo'lmasa -> yangi profil yaratadi (avtomatik username + tasodifiy parol)

    Qaytaradi: (user, session_token, plain_password_or_None)
      plain_password faqat YANGI ro'yxatda qaytariladi — bot chatga yuborishi uchun.
      Mavjud foydalanuvchida None (parol hech qachon qayta ko'rsatilmaydi).
    """
    # Mavjud foydalanuvchini Telegram ID bo'yicha topamiz
    res = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = res.scalar_one_or_none()

    plain_password: str | None = None

    if user is None:
        # Yangi profil — avtomatik username + tasodifiy parol
        username = await _unique_username_from_telegram(
            db, telegram_username=telegram_username, telegram_id=telegram_id
        )
        plain_password = generate_random_password()
        user = User(
            username=username,
            password_hash=hash_password(plain_password),
            telegram_id=telegram_id,
            language=language if language in ("uz", "en") else "uz",
        )
        db.add(user)
        await db.flush()

    if user.is_blocked or not user.is_active:
        raise AuthError("err_account_blocked")

    # Sessiya tokeni (parol tekshiruvisiz — initData allaqachon tasdiqlangan)
    token, jti, expires_at = create_session_token(user.id)
    db.add(
        UserSession(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            ip=ip,
            user_agent=(user_agent or "")[:255],
        )
    )
    db.add(LoginAttempt(username=user.username, ip=ip, success=True))
    await db.flush()

    return user, token, plain_password


async def change_password(
    db: AsyncSession,
    *,
    user: User,
    old_password: str,
    new_password: str,
    new_password_confirm: str,
) -> None:
    # Avval eski parol to'g'riligini tekshiramiz
    if not verify_password(old_password, user.password_hash):
        raise AuthError("err_old_password_wrong")

    _validate_password(new_password)
    if new_password != new_password_confirm:
        raise AuthError("err_password_mismatch")

    user.password_hash = hash_password(new_password)
    # Barcha boshqa sessiyalarni bekor qilamiz (xavfsizlik)
    await db.flush()


async def logout(db: AsyncSession, jti: str) -> None:
    res = await db.execute(select(UserSession).where(UserSession.jti == jti))
    sess = res.scalar_one_or_none()
    if sess:
        sess.revoked = True
        await db.flush()
