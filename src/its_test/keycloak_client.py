from keycloak import KeycloakAdmin, KeycloakOpenID, KeycloakOpenIDConnection

from .config import settings

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
