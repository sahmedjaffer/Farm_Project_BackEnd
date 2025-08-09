import httpx,asyncio,json,os
from services.exchange_rate import ExchangeRateService
from redis_client import redis_client
from services.http_client import cached_get
from models.hotel import Hotel , hotel_pydantic, hotel_pydanticIn
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
    cache_key = f"hotel_location_id:{city_name.lower()}"
    cached = await redis_client.get(cache_key)
    if cached:
        # ✅ يدعم سواء كانت القيمة bytes أو str
        return cached.decode() if isinstance(cached, bytes) else cached

    params = {"query": city_name}
    response = await client.get(os.getenv("HOTEL_AUTO_COMPLETE_URL"), headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    if not data.get("data"):
        return None

    location_id = data["data"][0]["id"]
    await redis_client.setex(cache_key, 86400, str(location_id))  # Cache 24h
    return location_id


async def get_hotels_data(location_id: str, arrival_date: str, departure_date: str, client: httpx.AsyncClient, page: int, sortBy: int):
    params = {
        "locationId": location_id,
        "checkinDate": arrival_date,
        "checkoutDate": departure_date,
        "sortBy": "price",
        "units": "metric",
        "page":page,
        "sortBy":sortBy
    }
    data = await cached_get(os.getenv("HOTEL_SEARCH_URL"), params=params, headers=HEADERS, ttl=CACHE_TTL) 
    return data.get("data", [])


async def get_hotel_reviews(hotel_id: int, client: httpx.AsyncClient):
    cache_key = f"hotel_reviews:{hotel_id}"

    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data.decode() if isinstance(cached_data, bytes) else cached_data)

    async with semaphore:
        params = {"hotelId": hotel_id}
        response = await client.get(os.getenv("HOTEL_REVIEW_SCORES_URL"), headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()

    await redis_client.setex(cache_key, 21600, json.dumps(data))  # Cache 6h
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

    price = hotel.get("priceBreakdown", {}).get("grossPrice", {}).get("value")
    currency = hotel.get("priceBreakdown", {}).get("grossPrice", {}).get("currency")

    price_in_bhd = None
    if price is not None and currency:
        price_in_bhd = await ExchangeRateService.convert_to_bhd(price, currency)

    return {
        "hotel_id": hotel.get("id"),
        "hotel_name": hotel.get("name"),
        "review_scoreWord": hotel.get("reviewScoreWord"),
        "review_score": hotel.get("reviewScore"),
        "local_price": price_in_bhd,
        "currency": "BHD" if price_in_bhd else currency,
        "original_price": price,
        "original_currency": currency,
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


async def post_hotel_service(hotel_info:hotel_pydanticIn):
    
    
    
    hotel_obj = await Hotel.create(
        hotel_name = hotel_info.hotel_name,
        hotel_review_score_word=hotel_info.hotel_review_score_word,
        hotel_review_score= hotel_info.hotel_review_score,
        hotel_gross_price= hotel_info.hotel_gross_price,
        hotel_currency=hotel_info.hotel_currency,
        hotel_check_in=hotel_info.hotel_check_in,
        hotel_check_out=hotel_info.hotel_check_out,
        hotel_score = hotel_info.hotel_score,
    )
    return {
        "status": "Ok",
        "data": await hotel_pydantic.from_tortoise_orm(hotel_obj)
    }