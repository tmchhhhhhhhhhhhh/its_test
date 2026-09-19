import secrets
import uuid

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from its_test.config import settings
from its_test.db import get_db
from its_test.deps import CurrentSession, get_current_session, get_current_user
from its_test.email import send_verification_email
from its_test.models import User
from its_test.redis import (
    create_email_verification_token,
    create_session,
    delete_session,
    pop_email_verification_token,
    redis_client,
)
from its_test.schemas import MessageOut, TokenOut, UserCreate, UserLogin, UserOut
from its_test.utils import (
    create_access_token,
    hash_password,
    verify_password,
)

app = FastAPI()


@app.get("/health")
async def healthcheck(db: AsyncSession = Depends(get_db)):
    report = {"status": "ok", "database": "ok", "redis": "ok"}

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        report["database"] = "unavailable"
        report["status"] = "degraded"

    try:
        await redis_client.ping()
    except Exception:
        report["redis"] = "unavailable"
        report["status"] = "degraded"

    return report


@app.post(
    "/auth/register", response_model=MessageOut, status_code=status.HTTP_201_CREATED
)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с такой почтой уже существует",
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = secrets.token_urlsafe(32)
    await create_email_verification_token(
        token, str(user.id), ttl_seconds=settings.email_token_expire_minutes * 60
    )
    await send_verification_email(user.email, token)

    return MessageOut(
        message="Регистрация выполнена. Проверьте почту для подтверждения аккаунта"
    )


@app.get("/auth/verify-email", response_model=MessageOut)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    user_id = await pop_email_verification_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Токен недействителен или истёк",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )

    user.is_verified = True
    await db.commit()

    return MessageOut(message="Почта успешно подтверждена")


@app.post("/auth/login", response_model=TokenOut)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверная почта или пароль"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Почта не подтверждена"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт деактивирован"
        )

    token, jti, expire = create_access_token(str(user.id))
    await create_session(
        jti, str(user.id), ttl_seconds=settings.access_token_expire_minutes * 60
    )

    return TokenOut(access_token=token, expires_at=expire.isoformat())


@app.post("/auth/logout", response_model=MessageOut)
async def logout(session: CurrentSession = Depends(get_current_session)):
    await delete_session(session.jti)
    return MessageOut(message="Вы вышли из системы")


@app.get("/auth/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)):
    """протектед ручка для теста сессии"""
    return current_user


@app.delete("/auth/me", response_model=MessageOut)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.delete(current_user)
    await db.commit()
    return MessageOut(message="Аккаунт удалён")
