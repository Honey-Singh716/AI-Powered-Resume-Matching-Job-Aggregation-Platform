import os
import json
import logging
import time
from typing import Optional

import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_REDIS_URL = "redis://localhost:6379/0"
REDIS_URL = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
RETRY_COOLDOWN_SECONDS = 30

_redis_client: Optional[redis.Redis] = None
_redis_last_attempt: float = 0.0


def get_redis_client(force: bool = False) -> Optional[redis.Redis]:
    global _redis_client, _redis_last_attempt
    if _redis_client is not None:
        return _redis_client

    now = time.time()
    if not force and now - _redis_last_attempt < RETRY_COOLDOWN_SECONDS:
        return None

    _redis_last_attempt = now
    try:
        logger.info("Initializing Redis connection to %s", REDIS_URL)
        client = redis.Redis.from_url(
            REDIS_URL,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            decode_responses=True,
        )
        client.ping()
        _redis_client = client
        logger.info("Redis connection established successfully.")
    except Exception as e:
        logger.warning("Redis unavailable at %s: %s. Caching disabled.", REDIS_URL, e)
        _redis_client = None

    return _redis_client


def init_redis() -> bool:
    """Eagerly connect to Redis during app startup."""
    return get_redis_client(force=True) is not None


def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception as e:
            logger.warning("Error closing Redis connection: %s", e)
        finally:
            _redis_client = None


def get_cached_recommendations(user_id: int, limit: int, skip: int) -> Optional[list]:
    client = get_redis_client()
    if not client:
        return None
    key = f"recommendations:{user_id}:{limit}:{skip}"
    try:
        data = client.get(key)
        if data:
            logger.info("Cache HIT for key: %s", key)
            return json.loads(data)
        logger.info("Cache MISS for key: %s", key)
    except Exception as e:
        logger.error("Redis get error: %s", e)
    return None


def set_cached_recommendations(user_id: int, limit: int, skip: int, data: list, expire_seconds: int = 600):
    client = get_redis_client()
    if not client:
        return
    key = f"recommendations:{user_id}:{limit}:{skip}"
    try:
        client.setex(key, expire_seconds, json.dumps(data))
        logger.info("Cached recommendations set for key: %s (expires in %ss)", key, expire_seconds)
    except Exception as e:
        logger.error("Redis set error: %s", e)


def invalidate_candidate_recommendations(user_id: int):
    client = get_redis_client()
    if not client:
        return
    pattern = f"recommendations:{user_id}:*"
    try:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
            logger.info("Invalidated %s cached recommendation keys for user %s", len(keys), user_id)
    except Exception as e:
        logger.error("Redis invalidation error: %s", e)
