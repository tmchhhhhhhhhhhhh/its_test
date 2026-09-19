import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from its_test.config import settings

password_hash = PasswordHash.recommended()  

def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> tuple[str, str, datetime]:
    jti = str(uuid.uuid4())
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti, expire


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise ValueError("Невалидный или просроченный токен") from exc
    if payload.get("type") != "access":
        raise ValueError("Неверный тип токена")
    return payload