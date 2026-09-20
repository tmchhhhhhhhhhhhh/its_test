from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from keycloak.exceptions import KeycloakAuthenticationError

from keycloak import KeycloakAdmin, KeycloakOpenID, KeycloakOpenIDConnection

from .config import settings

bearer_scheme = HTTPBearer(
    scheme_name="JWT",
    description="сюда access токен",
    auto_error=False, 
)

keycloak_openid = KeycloakOpenID(
    server_url=settings.keycloak_url,
    realm_name=settings.keycloak_realm,
    client_id=settings.keycloak_client_id,
    client_secret_key=settings.keycloak_client_secret,
)

keycloak_admin_connection = KeycloakOpenIDConnection(
    server_url=settings.keycloak_url,
    username=settings.keycloak_admin_user,
    password=settings.keycloak_admin_password,
    realm_name="its-test",
    user_realm_name="master", 
    client_id="admin-cli",
    verify=True,
)
keycloak_admin = KeycloakAdmin(connection=keycloak_admin_connection)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        userinfo = await keycloak_openid.a_userinfo(credentials.credentials)
    except KeycloakAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен недействителен") from exc
    return userinfo