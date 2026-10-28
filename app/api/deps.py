"""FastAPI dependency'lar: joriy foydalanuvchi, admin tekshiruvi, til."""
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decode_session_token
from app.database import get_db
from app.i18n import t
from app.models.settings import AdminUser
from app.models.user import Session as UserSession, User


def get_lang(accept_language: str | None = Header(default=None)) -> str:
    """So'rovdan tilni aniqlaydi (foydalanuvchi profili ustuvorroq)."""
    if accept_language and accept_language.lower().startswith("en"):
        return "en"
    return "uz"


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authorization: Bearer <token> orqali joriy foydalanuvchini qaytaradi."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("err_not_authenticated", get_lang(request.headers.get("accept-language"))),
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_session_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail=t("err_not_authenticated"))

    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or not user_id:
        raise HTTPException(status_code=401, detail=t("err_not_authenticated"))

    # Sessiya bekor qilinmaganmi / amal qilyaptimi
    res = await db.execute(select(UserSession).where(UserSession.jti == jti))
    sess = res.scalar_one_or_none()
    if not sess or sess.revoked:
        raise HTTPException(status_code=401, detail=t("err_not_authenticated"))
    if sess.expires_at:
        # SQLite timezone saqlamaydi -> naive datetime qaytaradi.
        # Naive bo'lsa UTC deb hisoblab, aware bilan solishtiramiz.
        expires_at = sess.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail=t("err_not_authenticated"))

    res = await db.execute(select(User).where(User.id == int(user_id)))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail=t("err_not_authenticated"))
    if user.is_blocked:
        raise HTTPException(status_code=403, detail=t("err_account_blocked", user.language))

    # jti ni request state ga qo'yamiz (logout uchun)
    request.state.jti = jti
    return user


async def require_admin(
    x_admin_telegram_id: int | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> int:
    """
    Admin huquqini SERVER TOMONIDA tekshiradi.
    Admin ID .env (ADMIN_TELEGRAM_IDS) yoki admin_users jadvalida bo'lishi kerak.

    ⚠️ Prod'da bu header Nginx/Telegram initData orqali ishonchli tarzda
    o'rnatilishi kerak. Oddiy username bilan admin bo'lib bo'lmaydi.
    """
    if x_admin_telegram_id is None:
        raise HTTPException(status_code=403, detail=t("err_forbidden"))

    # 1) .env ro'yxati
    if x_admin_telegram_id in settings.admin_ids:
        return x_admin_telegram_id

    # 2) admin_users jadvali
    res = await db.execute(
        select(AdminUser).where(
            AdminUser.telegram_id == x_admin_telegram_id,
            AdminUser.is_active == True,  # noqa: E712
        )
    )
    if res.scalar_one_or_none():
        return x_admin_telegram_id

    raise HTTPException(status_code=403, detail=t("err_forbidden"))
