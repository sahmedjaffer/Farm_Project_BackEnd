import json, httpx ,asyncio
from redis_client import redis_client

semaphore = asyncio.Semaphore(3)

async def cached_get(url: str, params=None, headers=None, ttl: int = 3600):

    cache_key = f"http_cache:{url}:{json.dumps(params, sort_keys=True)}"
    
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    async with semaphore:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 429:
                await asyncio.sleep(2)
                response = await client.get(url, headers=headers, params=params)

            response.raise_for_status()
            data = response.json()

    await redis_client.setex(cache_key, ttl, json.dumps(data))
    return data
