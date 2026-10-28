"""Autentifikatsiya API: ro'yxat, login, logout, parol, til."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.telegram_auth import TelegramAuthError, validate_init_data
from app.database import get_db
from app.i18n import t
from app.models.user import User
from app.schemas.schemas import (
    ChangePasswordIn,
    LanguageIn,
    LoginIn,
    ProfileOut,
    RegisterIn,
    TelegramAuthIn,
    TokenOut,
)
from app.services import auth_service, bot_notify_service, support_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/register", response_model=TokenOut)
async def register(payload: RegisterIn, request: Request, db: AsyncSession = Depends(get_db)):
    telegram_id = None
    # Telegram initData ixtiyoriy; bo'lsa tekshiramiz
    if payload.init_data:
        try:
            info = validate_init_data(payload.init_data)
            telegram_id = info.get("telegram_id")
        except TelegramAuthError:
            # initData noto'g'ri bo'lsa rad etamiz (soxta bo'lmasin)
            raise HTTPException(status_code=400, detail=t("err_invalid_initdata", payload.language))

    try:
        user = await auth_service.register(
            db,
            username=payload.username,
            password=payload.password,
            password_confirm=payload.password_confirm,
            telegram_id=telegram_id,
            language=payload.language,
        )
    except AuthError as e:
        raise HTTPException(status_code=400, detail=t(e.key, payload.language))

    # Avtomatik login
    _, token = await auth_service.login(
        db,
        username=user.username,
        password=payload.password,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return TokenOut(token=token, username=user.username, language=user.language)


@router.post("/telegram", response_model=TokenOut)
async def telegram_auth(
    payload: TelegramAuthIn, request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Telegram WebApp initData orqali AVTOMATIK autentifikatsiya.

    - initData server tomonida HMAC bilan tekshiriladi (soxta bo'lmasin).
    - Foydalanuvchi bo'lsa -> kiritadi; bo'lmasa -> yangi profil yaratadi.
    - Yangi profil yaratilganda bot chatga username + parolni yuboradi.
    - Parol so'ralmaydi; foydalanuvchi to'g'ridan-to'g'ri katalogga o'tadi.
    """
    # 1) initData ni tekshiramiz
    try:
        info = validate_init_data(payload.init_data)
    except TelegramAuthError:
        raise HTTPException(status_code=400, detail=t("err_invalid_initdata", payload.language))

    telegram_id = info.get("telegram_id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail=t("err_invalid_initdata", payload.language))

    tg_username = info.get("username")
    lang_code = (info.get("language_code") or payload.language or "uz")
    language = "en" if str(lang_code).lower().startswith("en") else "uz"

    # 2) Avtomatik autentifikatsiya (yangi bo'lsa parol qaytadi)
    try:
        user, token, plain_password = await auth_service.auto_authenticate(
            db,
            telegram_id=int(telegram_id),
            telegram_username=tg_username,
            language=language,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as e:
        code = 403 if e.key == "err_account_blocked" else 400
        raise HTTPException(status_code=code, detail=t(e.key, language))

    # 3) Yangi profil bo'lsa — bot chatga username + parol yuboradi (bir marta)
    if plain_password:
        await bot_notify_service.send_credentials(
            telegram_id=int(telegram_id),
            username=user.username,
            password=plain_password,
            language=user.language,
        )

    return TokenOut(token=token, username=user.username, language=user.language)


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user, token = await auth_service.login(
            db,
            username=payload.username,
            password=payload.password,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as e:
        code = 429 if e.key == "err_too_many_attempts" else 401
        raise HTTPException(status_code=code, detail=t(e.key))
    return TokenOut(token=token, username=user.username, language=user.language)


@router.post("/logout")
async def logout(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    jti = getattr(request.state, "jti", None)
    if jti:
        await auth_service.logout(db, jti)
    return {"ok": True}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await auth_service.change_password(
            db,
            user=user,
            old_password=payload.old_password,
            new_password=payload.new_password,
            new_password_confirm=payload.new_password_confirm,
        )
    except AuthError as e:
        raise HTTPException(status_code=400, detail=t(e.key, user.language))
    return {"ok": True, "message": t("ok_password_changed", user.language)}


@router.post("/language", response_model=ProfileOut)
async def set_language(
    payload: LanguageIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.language = payload.language
    await db.flush()
    support = await support_service.get_support_username(db)
    return ProfileOut(
        id=user.id,
        username=user.username,
        language=user.language,
        balance_uzs=user.balance_uzs,
        created_at=user.created_at,
        support_username=support,
    )


@router.get("/me", response_model=ProfileOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    support = await support_service.get_support_username(db)
    return ProfileOut(
        id=user.id,
        username=user.username,
        language=user.language,
        balance_uzs=user.balance_uzs,
        created_at=user.created_at,
        support_username=support,
    )
