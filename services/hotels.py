from fastapi import Depends, HTTPException
import httpx, asyncio, json, os
from models.user import User
from services.exchange_rate import ExchangeRateService
from config.redis_client import get_redis_client
from services.http_client import cached_get
from models.hotel import Hotel, hotel_pydantic, hotel_pydanticIn
from dotenv import load_dotenv

# Load environment variables from .env before using os.getenv
load_dotenv()

CACHE_TTL = 86400  # Cache time-to-live in seconds (24 hours)

# Headers required for API calls, using credentials from environment variables
HEADERS = {
    "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
    "x-rapidapi-host": os.getenv("RAPID_API_HOST")
}

# Limit the number of concurrent requests to hotel reviews to avoid rate limiting
semaphore = asyncio.Semaphore(3)

async def get_location_id(city_name: str, client: httpx.AsyncClient):
    """
    Get the location ID for a given city from the hotel autocomplete API.
    Results are cached in Redis for 24 hours to reduce API calls.
    """
    cache_key = f"hotel_location_id:{city_name.lower()}"
    cached = await get_redis_client().get(cache_key)
    if cached:
        # Return cached location ID if available (decode bytes to string if necessary)
        return cached.decode() if isinstance(cached, bytes) else cached

    # If not cached, make API request to get location ID
    params = {"query": city_name}
    response = await client.get(os.getenv("HOTEL_AUTO_COMPLETE_URL"), headers=HEADERS, params=params)
    response.raise_for_status()  # Raise exception for bad HTTP status codes
    data = response.json()
    if not data.get("data"):
        return None  # No location data found

    location_id = data["data"][0]["id"]
    # Cache the location ID in Redis for 24 hours
    await get_redis_client().setex(cache_key, 86400, str(location_id))
    return location_id


async def get_hotels_data(location_id: str, arrival_date: str, departure_date: str, client: httpx.AsyncClient, page: int, sortBy: int):
    """
    Retrieve hotel search results for a given location and date range.
    Uses cached_get utility to cache API responses for 24 hours.
    """
    params = {
        "locationId": location_id,
        "checkinDate": arrival_date,
        "checkoutDate": departure_date,
        "units": "metric",
        "page": page,
        "sortBy": sortBy
    }
    # Fetch data from hotel search API with caching
    data = await cached_get(os.getenv("HOTEL_SEARCH_URL"), params=params, headers=HEADERS, ttl=CACHE_TTL)
    return data.get("data", [])


async def get_hotel_reviews(hotel_id: int, client: httpx.AsyncClient):
    """
    Get review scores for a specific hotel ID.
    Results are cached in Redis for 6 hours.
    Limits concurrent requests with a semaphore.
    """
    cache_key = f"hotel_reviews:{hotel_id}"

    cached_data = await get_redis_client().get(cache_key)
    if cached_data:
        # Return cached review data if available (decode bytes if needed)
        return json.loads(cached_data.decode() if isinstance(cached_data, bytes) else cached_data)

    async with semaphore:
        await asyncio.sleep(0.4)
        params = {"hotelId": hotel_id}
        response = await client.get(os.getenv("HOTEL_REVIEW_SCORES_URL"), headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()

    # Cache the review data in Redis for 6 hours
    await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(data))
    return data

async def fetch_with_retry(client, url, params=None, max_retries=6):
    for attempt in range(max_retries):
        try:
            async with semaphore:
                response = await client.get(url, headers=HEADERS, params=params)
            if response.status_code == 429:
                await asyncio.sleep(2 ** attempt)  # exponential backoff
                continue
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await asyncio.sleep(2 ** attempt)
                continue
            raise
    raise Exception(f"Failed after {max_retries} retries due to 429 for URL: {url}")



async def get_hotel_full_detail(hotel_id: int, client: httpx.AsyncClient, arrival_date: str, departure_date: str):
    """
    Fetches hotel booking URL, address, spoken languages, and photo URL.
    Caches results in Redis for 6 hours.
    """
    cache_key = f"hotel_full_detail:{hotel_id}"
    cached_data = await get_redis_client().get(cache_key)
    if cached_data:
        cached_dict = json.loads(cached_data.decode() if isinstance(cached_data, bytes) else cached_data)

        data_content = cached_dict.get("data") or {}
        hotel_booking_url = data_content.get("url", "")
        hotel_address = data_content.get("hotel_address_line", "Address not available")
        spoken_lang = data_content.get("spoken_languages", [])
        hotel_photo_url = cached_dict.get("hotel_photo_url", "")
        return {
            "hotel_booking_url": hotel_booking_url,
            "hotel_address": hotel_address,
            "spoken_languages": spoken_lang,
            "hotel_photo_url": hotel_photo_url
        }


    # --- Fetch hotel details ---
    details_params = {"hotelId": hotel_id, "checkinDate": arrival_date, "checkoutDate": departure_date}
    details_data = await fetch_with_retry(client, os.getenv("HOTEL_DETAILS_URL"), details_params)
    # print(details_data)
    data_content = details_data.get("data")
    # print(data_content)
    hotel_booking_url = data_content.get("url")
    # print(hotel_booking_url)
    hotel_address = data_content.get("hotel_address_line")
    # print(hotel_address)


    # --- Fetch hotel photo ---
    photo_params = {"hotelId": hotel_id}
    photo_data = await fetch_with_retry(client, os.getenv("HOTEL_PHOTO_URL"), photo_params)
    try:
        hotel_photo = photo_data.get("data", {}).get("data", {}).get(str(hotel_id), [[[],[],[],[],[]]])[0][4][5]
        base_url = photo_data.get("data", {}).get("url_prefix", "")
    except (KeyError, IndexError, TypeError):
        hotel_photo = ""
        base_url = ""
    hotel_photo_url = base_url + hotel_photo

    full_detail = {
        "hotel_booking_url": hotel_booking_url,
        "hotel_address": hotel_address,
        "hotel_photo_url": hotel_photo_url
    }

    #Cache for 6 hours
    await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(full_detail))
    return full_detail


# ===== Build hotel info =====
async def assemble_hotel_info(hotel, review_scores, hotel_booking_url, hotel_photo_url, hotel_address, base_currency_code: str, base_currency_date: str):
    """
    Build a detailed dictionary of hotel info, including price converted to BHD,
    check-in/out times, and categorized review scores.
    """
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
        "hotel_address": hotel_address,
        "review_scoreWord": hotel.get("reviewScoreWord"),
        "review_score": hotel.get("reviewScore"),
        "hotel_booking_url": hotel_booking_url,
        "hotel_photo_url": hotel_photo_url,
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




hotelIn = hotel_pydanticIn
async def post_hotel_service(hotel_info: hotelIn, current_user: User):
    """
    Create a new hotel record in the database linked to the current user.
    Returns the saved hotel data in the response.
    """
    hotel_obj = await Hotel.create(
        hotel_name=hotel_info.hotel_name,
        hotel_review_score_word=hotel_info.hotel_review_score_word,
        hotel_review_score=hotel_info.hotel_review_score,
        hotel_gross_price=hotel_info.hotel_gross_price,
        hotel_currency=hotel_info.hotel_currency,
        hotel_check_in=hotel_info.hotel_check_in,
        hotel_check_out=hotel_info.hotel_check_out,
        hotel_score=hotel_info.hotel_score,
        related_user_id=current_user.id
    )
    return {
        "status": "Ok",
        "data": await hotel_pydantic.from_tortoise_orm(hotel_obj)
    }


async def get_all_hotels_service(current_user: User):
    """
    Retrieve all hotel records linked to the current user.
    Raises HTTP 404 if no hotels are found.
    """
    get_all_hotels_res = await hotel_pydantic.from_queryset(
        Hotel.filter(related_user=current_user.id)
    )
    if not get_all_hotels_res:
        raise HTTPException(status_code=404, detail="No hotels found for this user")
    return {"status": "Ok", "data": get_all_hotels_res}
