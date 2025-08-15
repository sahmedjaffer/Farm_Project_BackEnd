import json, httpx, asyncio
from redis.exceptions import ConnectionError, RedisError
from config.redis_client import get_redis_client

semaphore = asyncio.Semaphore(3)

async def cached_get(url: str, params=None, headers=None, ttl: int = 3600):
    cache_key = f"http_cache:{url}:{json.dumps(params, sort_keys=True)}"
    redis_client = get_redis_client()

    # Try to get cached data
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except (ConnectionError, RedisError) as e:
        print(f"Redis unavailable, using API: {e}")

    # Limit concurrent HTTP requests
    async with semaphore:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 429:  # Too Many Requests
                await asyncio.sleep(2)
                response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

    # Try to cache data, ignore failures
    try:
        await redis_client.setex(cache_key, ttl, json.dumps(data))
    except (ConnectionError, RedisError) as e:
        print(f"Failed to write cache: {e}")

    return data
