import httpx,asyncio,json
from services.exchange_rate import ExchangeRateService
from redis_client import redis_client
from services.http_client import cached_get
import os
from dotenv import load_dotenv

# Load .env before using os.getenv
load_dotenv() 

CACHE_TTL = 86400  # 24 hours

HEADERS = {
    "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
    "x-rapidapi-host": os.getenv("RAPID_API_HOST")
}



# Limit concurrent review requests
semaphore = asyncio.Semaphore(3)


async def get_location_id(city_name: str, client: httpx.AsyncClient):
    params = {"query": city_name}
    response = await client.get(os.getenv("HOTEL_AUTO_COMPLETE_URL"), headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    if not data.get("data"):
        return None
    return data["data"][0]["id"]


async def get_hotels_data(location_id: str, arrival_date: str, departure_date: str, client: httpx.AsyncClient):
    params = {
        "locationId": location_id,
        "checkinDate": arrival_date,
        "checkoutDate": departure_date,
        "sortBy": "price",
        "units": "metric",
        "temperature": "c"
    }
    data = await cached_get(os.getenv("HOTEL_SEARCH_URL"), params=params, headers=HEADERS, ttl=CACHE_TTL) 
    return data.get("data", [])


async def get_hotel_reviews(hotel_id: int, client: httpx.AsyncClient):
    cache_key = f"hotel_reviews:{hotel_id}"

    # 1️⃣ Try to get from cache first
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # 2️⃣ Otherwise, fetch from API (limit concurrency)
    async with semaphore:
        params = {"hotelId": hotel_id}
        response = await client.get(os.getenv("HOTEL_REVIEW_SCORES_URL"), headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()

    # 3️⃣ Store in cache for 6 hour
    await redis_client.setex(cache_key, 21600, json.dumps(data))

    return data


async def build_hotel_info(hotel, review_scores, base_currency_code: str, base_currency_date: str):
    score_percentages = review_scores.get("data", {}).get("score_percentage", [])

    def safe_score(index):
        if len(score_percentages) > index:
            return {
                "percent": score_percentages[index].get("percent"),
                "count": score_percentages[index].get("count"),
            }
        return {"percent": None, "count": None}

    # Get price and currency from hotel data
    price = hotel.get("priceBreakdown", {}).get("grossPrice", {}).get("value")
    currency = hotel.get("priceBreakdown", {}).get("grossPrice", {}).get("currency")

    # Convert to BHD if possible
    price_in_bhd = None
    if price is not None and currency:
        price_in_bhd = await ExchangeRateService.convert_to_bhd(price, currency)

    return {
        "hotel_id": hotel.get("id"),
        "hotel_name": hotel.get("name"),
        "review_scoreWord": hotel.get("reviewScoreWord"),
        "review_score": hotel.get("reviewScore"),
        "gross_price": price_in_bhd,
        "currency": "BHD",
        "base_currency": base_currency_code,
        "base_currency_date": base_currency_date,
        "check_in": {
            "from": hotel.get("checkin", {}).get("fromTime"),
            "until": hotel.get("checkin", {}).get("untilTime"),
        },
        "check_out": {
            "from": hotel.get("checkout", {}).get("fromTime"),
            "until": hotel.get("checkout", {}).get("untilTime"),
        },
        "score": {
            "Wonderful": safe_score(0),
            "Good": safe_score(1),
            "Okay": safe_score(2),
            "Poor": safe_score(3),
            "Very Poor": safe_score(4),
        }
    }
