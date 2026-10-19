"""Parol xeshlash va JWT sessiya tokenlari."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

# bcrypt — parollar uchun
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_session_token(user_id: int, jti: str | None = None) -> tuple[str, str, datetime]:
    """JWT yaratadi. (token, jti, expires_at) qaytaradi."""
    jti = jti or uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.session_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, jti, expires_at


def decode_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
