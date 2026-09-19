import redis.asyncio as aioredis

from its_test.config import settings

redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

SESSION_PREFIX = "session:"            
EMAIL_VERIFY_PREFIX = "email_verify:" 


async def create_session(jti: str, user_id: str, ttl_seconds: int) -> None:
    await redis_client.set(f"{SESSION_PREFIX}{jti}", user_id, ex=ttl_seconds)


async def get_session_user_id(jti: str) -> str | None:
    result = await redis_client.get(f"{SESSION_PREFIX}{jti}")
    if isinstance(result, bytes):
        return result.decode()
    return result


async def delete_session(jti: str) -> None:
    await redis_client.delete(f"{SESSION_PREFIX}{jti}")


async def create_email_verification_token(token: str, user_id: str, ttl_seconds: int) -> None:
    await redis_client.set(f"{EMAIL_VERIFY_PREFIX}{token}", user_id, ex=ttl_seconds)


async def pop_email_verification_token(token: str) -> str | None:
    key = f"{EMAIL_VERIFY_PREFIX}{token}"
    user_id = await redis_client.get(key)
    if user_id is not None:
        await redis_client.delete(key)
    if isinstance(user_id, bytes):
        return user_id.decode()
    return user_id
