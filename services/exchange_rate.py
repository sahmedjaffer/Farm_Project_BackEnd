import time
import json
import httpx
from fastapi import HTTPException
from redis_client import redis_client
import os
from dotenv import load_dotenv

# Load .env before using os.getenv
load_dotenv()  

HEADERS = {
    "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
    "x-rapidapi-host": os.getenv("RAPID_API_HOST")
}

TIMEOUT = 10.0

CACHE_TTL = 86400  


class ExchangeRateService:
    _rates_cache = None
    _last_fetch_time = 0

    @classmethod
    async def get_rates(cls, base_currency: str = "BHD") -> dict:
        """Get exchange rates from Redis or API (cached for 24h)"""
        current_time = time.time()

        if cls._rates_cache is not None and (current_time - cls._last_fetch_time) < CACHE_TTL:
            return cls._rates_cache

        redis_key = f"exchange_rates:{base_currency}"
        cached = await redis_client.get(redis_key)
        if cached:
            data = json.loads(cached)
            cls._rates_cache = data
            cls._last_fetch_time = current_time
            return data

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            params = {"baseCurrency": base_currency}
            resp = await client.get(os.getenv("EXCHANGE_RATE_URL"), headers=HEADERS, params=params)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch exchange rates")

            data = resp.json()
            base_currency_code = data.get("data", {}).get("base_currency", base_currency)
            base_currency_date = data.get("data", {}).get("base_currency_date", "")
            rates_list = data.get("data", {}).get("exchange_rates", [])

            rates_dict = {
                r.get("currency"): r.get("exchange_rate_buy")
                for r in rates_list if r.get("currency") and r.get("exchange_rate_buy")
            }

            result = {
                "base_currency": base_currency_code,
                "base_currency_date": base_currency_date,
                "rates": rates_dict
            }

            await redis_client.setex(redis_key, CACHE_TTL, json.dumps(result))

            cls._rates_cache = result
            cls._last_fetch_time = current_time
            return result

    @classmethod
    async def convert_to_bhd(cls, amount: float, from_currency: str) -> float:
        """Convert given amount from another currency to BHD"""
        if from_currency == "BHD":
            return round(amount, 3)

        rates_data = await cls.get_rates()
        rates = rates_data.get("rates", {})

        rate = rates.get(from_currency)
        if not rate:
            raise HTTPException(status_code=400, detail=f"Exchange rate for {from_currency} not found")

        converted_amount = float(amount) / float(rate)
        return round(converted_amount, 3)

    @classmethod
    async def reset_cache(cls, base_currency: str = "BHD"):
        """Manually reset both in-memory and Redis cache"""
        cls._rates_cache = None
        cls._last_fetch_time = 0
        redis_key = f"exchange_rates:{base_currency}"
        await redis_client.delete(redis_key)
