import time
import json
import httpx
from fastapi import HTTPException
from config.redis_client import redis_client
import os
from dotenv import load_dotenv

# Load environment variables from the .env file before accessing them
load_dotenv()  

# Set headers for API requests, using keys from environment variables
HEADERS = {
    "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
    "x-rapidapi-host": os.getenv("RAPID_API_HOST")
}

# Timeout for HTTP requests in seconds
TIMEOUT = 10.0

# Cache time-to-live (TTL) in seconds, here 24 hours
CACHE_TTL = 86400  


class ExchangeRateService:
    # Class variables to hold in-memory cached rates and timestamp of last fetch
    _rates_cache = None
    _last_fetch_time = 0

    @classmethod
    async def get_rates(cls, base_currency: str = "BHD") -> dict:
        """
        Retrieve exchange rates for the given base currency.
        Uses both in-memory and Redis cache to reduce external API calls.
        Cache expires after CACHE_TTL seconds (24 hours).
        """
        current_time = time.time()

        # Check if cached data exists in memory and is still valid
        if cls._rates_cache is not None and (current_time - cls._last_fetch_time) < CACHE_TTL:
            return cls._rates_cache

        # Try to get cached data from Redis
        redis_key = f"exchange_rates:{base_currency}"
        cached = await redis_client.get(redis_key)
        if cached:
            data = json.loads(cached)
            # Update in-memory cache and last fetch time
            cls._rates_cache = data
            cls._last_fetch_time = current_time
            return data

        # If no cache or expired, fetch fresh data from external API
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            params = {"baseCurrency": base_currency}
            resp = await client.get(os.getenv("EXCHANGE_RATE_URL"), headers=HEADERS, params=params)

            # If API response is not successful, raise an HTTP error
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch exchange rates")

            data = resp.json()

            # Extract relevant information from API response
            base_currency_code = data.get("data", {}).get("base_currency", base_currency)
            base_currency_date = data.get("data", {}).get("base_currency_date", "")
            rates_list = data.get("data", {}).get("exchange_rates", [])

            # Convert list of rates into a dictionary mapping currency codes to exchange rate values
            rates_dict = {
                r.get("currency"): r.get("exchange_rate_buy")
                for r in rates_list if r.get("currency") and r.get("exchange_rate_buy")
            }

            # Prepare the final result dict with base currency info and rates dictionary
            result = {
                "base_currency": base_currency_code,
                "base_currency_date": base_currency_date,
                "rates": rates_dict
            }

            # Cache the result in Redis for subsequent requests
            await redis_client.setex(redis_key, CACHE_TTL, json.dumps(result))

            # Update in-memory cache and timestamp
            cls._rates_cache = result
            cls._last_fetch_time = current_time
            return result

    @classmethod
    async def convert_to_bhd(cls, amount: float, from_currency: str) -> float:
        """
        Convert a given amount from a specified currency to BHD.
        Uses cached exchange rates to perform conversion.
        """
        # If currency is already BHD, no conversion needed
        if from_currency == "BHD":
            return round(amount, 3)

        # Get latest exchange rates (cached or fresh)
        rates_data = await cls.get_rates()
        rates = rates_data.get("rates", {})

        # Get exchange rate for the source currency
        rate = rates.get(from_currency)

        # If rate is missing, raise an HTTP error
        if not rate:
            raise HTTPException(status_code=400, detail=f"Exchange rate for {from_currency} not found")

        # Calculate converted amount by dividing amount by the rate
        converted_amount = float(amount) / float(rate)

        # Return converted amount rounded to 3 decimal places
        return round(converted_amount, 3)

    @classmethod
    async def reset_cache(cls, base_currency: str = "BHD"):
        """
        Manually clear both in-memory and Redis cache for exchange rates.
        Useful to force refresh of rates.
        """
        cls._rates_cache = None
        cls._last_fetch_time = 0
        redis_key = f"exchange_rates:{base_currency}"
        await redis_client.delete(redis_key)
