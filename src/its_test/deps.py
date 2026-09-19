import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from its_test.db import get_db
from its_test.models import User
from its_test.redis import get_session_user_id
from its_test.utils import decode_access_token


@dataclass
class CurrentSession:
    user: User
    jti: str

bearer_scheme = HTTPBearer(
    scheme_name="JWT",
    description="сюда access токен",
    auto_error=False, 
)

async def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentSession:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует заголовок Authorization",
        )
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    
    jti = payload.get("jti")
    user_id = payload.get("sub")
    if jti is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен повреждён")
    session_user_id = await get_session_user_id(jti)
    if session_user_id is None or session_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия недействительна или истекла")

    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Некорректный идентификатор пользователя")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    
    return CurrentSession(user=user, jti=jti)


async def get_current_user(session: CurrentSession = Depends(get_current_session)) -> User:
    return session.user