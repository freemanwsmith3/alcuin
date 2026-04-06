from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)
from app.rag import db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    async with db.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE username = $1", body.username
        )
        if existing:
            raise HTTPException(status_code=409, detail="Username already taken")

        row = await conn.fetchrow(
            """INSERT INTO users (username, email, password_hash)
               VALUES ($1, $2, $3)
               RETURNING id, username, email""",
            body.username,
            body.email,
            hash_password(body.password),
        )
    return UserOut(id=str(row["id"]), username=row["username"], email=row["email"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, password_hash FROM users WHERE username = $1 AND is_active = true",
            body.username,
        )
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id = str(row["id"])
    redis = request.app.state.redis
    access_token = create_access_token(user_id, body.username)
    refresh_token = await create_refresh_token(redis, user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, request: Request):
    redis = request.app.state.redis
    try:
        new_refresh, user_id = await rotate_refresh_token(redis, body.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT username FROM users WHERE id = $1 AND is_active = true", user_id
        )
    if not row:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(user_id, row["username"])
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, request: Request):
    redis = request.app.state.redis
    await revoke_refresh_token(redis, body.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser = Depends(get_current_user)):
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, email FROM users WHERE id = $1", current_user.id
        )
    return UserOut(id=str(row["id"]), username=row["username"], email=row["email"])
