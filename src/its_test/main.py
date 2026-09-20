from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from keycloak.exceptions import KeycloakAuthenticationError, KeycloakPostError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from its_test.db import get_db
from its_test.schemas import MessageOut, TokenOut, UserCreate, UserLogin

from .keycloak_client import keycloak_admin, keycloak_openid

app = FastAPI()

bearer_scheme = HTTPBearer(
    scheme_name="JWT",
    description="сюда access токен",
    auto_error=False, 
)


@app.get("/health")
async def healthcheck(db: AsyncSession = Depends(get_db)):
    report = {"status": "ok", "database": "ok"}

    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        report["database"] = "unavailable"
        report["status"] = "degraded"

    return report

@app.post("/auth/register", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate):
    try:
        user_id = keycloak_admin.create_user(
            {
                "email": data.email,
                "username": data.email,
                "enabled": True,
                "emailVerified": False,
                "firstName": " ",
                "lastName": " ",
                "credentials": [{"type": "password", "value": data.password, "temporary": False}],
            }
        )
    except KeycloakAuthenticationError as exc:
        raise HTTPException(status_code=502, detail="Не удалось подключиться к Keycloak как admin") from exc
    except KeycloakPostError as exc:
        raise HTTPException(status_code=409, detail="Пользователь уже существует") from exc

    keycloak_admin.send_verify_email(user_id=user_id)
    return MessageOut(message="Регистрация выполнена. Проверьте почту для подтверждения аккаунта")


@app.post("/auth/login", response_model=TokenOut)
async def login(data: UserLogin):
    try:
        token = await keycloak_openid.a_token(data.email, data.password)
    except KeycloakAuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Неверная почта или пароль") from exc

    userinfo = await keycloak_openid.a_userinfo(token["access_token"])
    if not userinfo.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Почта не подтверждена")

    return TokenOut(access_token=token["access_token"], expires_at="")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        userinfo = await keycloak_openid.a_userinfo(credentials.credentials)
    except KeycloakAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен недействителен") from exc
    return userinfo


@app.post("/auth/refresh", response_model=TokenOut)
async def refresh(refresh_token: str):
    token = await keycloak_openid.a_refresh_token(refresh_token)
    return TokenOut(access_token=token["access_token"], expires_at="")


@app.get("/auth/me")
async def read_me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.post("/auth/logout", response_model=MessageOut)
async def logout(data: dict): 
    await keycloak_openid.a_logout(data["refresh_token"])
    return MessageOut(message="Вы вышли из системы")


@app.delete("/auth/me", response_model=MessageOut)
async def delete_account(current_user: dict = Depends(get_current_user)):
    keycloak_admin.delete_user(user_id=current_user["sub"])
    return MessageOut(message="Аккаунт удалён")