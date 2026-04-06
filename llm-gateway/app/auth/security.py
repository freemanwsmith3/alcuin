import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
REFRESH_TOKEN_PREFIX = "refresh_token:"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "username": username, "exp": expire, "type": "access"}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises JWTError if invalid or expired."""
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("not an access token")
    return payload


async def create_refresh_token(redis, user_id: str) -> str:
    token = str(uuid.uuid4())
    key = REFRESH_TOKEN_PREFIX + token
    ttl = REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.set(key, user_id, ex=ttl)
    return token


async def rotate_refresh_token(redis, old_token: str) -> tuple[str, str]:
    """Consume old refresh token, return (new_refresh_token, user_id).
    Raises ValueError if the token is invalid or already used.
    """
    key = REFRESH_TOKEN_PREFIX + old_token
    user_id = await redis.getdel(key)
    if not user_id:
        raise ValueError("invalid or expired refresh token")
    if isinstance(user_id, bytes):
        user_id = user_id.decode()
    new_token = await create_refresh_token(redis, user_id)
    return new_token, user_id


async def revoke_refresh_token(redis, token: str) -> None:
    await redis.delete(REFRESH_TOKEN_PREFIX + token)
