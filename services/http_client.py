import json, httpx, asyncio
from config.redis_client import get_redis_client

# Limit concurrent HTTP requests to avoid overwhelming the API or hitting rate limits
semaphore = asyncio.Semaphore(3)

async def cached_get(url: str, params=None, headers=None, ttl: int = 3600):
    """
    Make an HTTP GET request with caching using Redis.
    If cached response exists, return it to avoid repeated calls.
    Use a semaphore to limit concurrency and handle 429 rate limit errors with retry.
    """

    # Create a unique cache key using URL and sorted JSON parameters for consistency
    cache_key = f"http_cache:{url}:{json.dumps(params, sort_keys=True)}"
    
    # Try to get cached response data from Redis
    cached_data = await get_redis_client().get(cache_key)
    if cached_data:
        # If cached data found, deserialize JSON and return immediately
        return json.loads(cached_data)
    
    # If no cached data, acquire semaphore to limit concurrent requests
    async with semaphore:
        # Create an HTTPX async client with a 30-second timeout
        async with httpx.AsyncClient(timeout=30) as client:
            # Send GET request with given headers and parameters
            response = await client.get(url, headers=headers, params=params)
            
            # If the response status is 429 (Too Many Requests), wait and retry once
            if response.status_code == 429:
                await asyncio.sleep(2)
                response = await client.get(url, headers=headers, params=params)

            # Raise exception for other non-successful status codes
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

    # Cache the response data in Redis with specified TTL (time-to-live)
    await get_redis_client().setex(cache_key, ttl, json.dumps(data))
    
    # Return the fresh response data
    return data
