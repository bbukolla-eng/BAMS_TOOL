import redis.asyncio as aioredis
from redis.asyncio import Redis

from core.config import settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def publish_job_progress(job_id: str, progress: dict) -> None:
    r = await get_redis()
    import json
    await r.publish(f"job:{job_id}", json.dumps(progress))


async def set_job_status(job_id: str, status: dict, ttl: int = 3600) -> None:
    r = await get_redis()
    import json
    await r.setex(f"job_status:{job_id}", ttl, json.dumps(status))


async def get_job_status(job_id: str) -> dict | None:
    r = await get_redis()
    import json
    val = await r.get(f"job_status:{job_id}")
    return json.loads(val) if val else None
