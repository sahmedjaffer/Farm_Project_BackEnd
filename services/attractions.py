from fastapi import HTTPException
import httpx, asyncio, json,os
from models.attraction import Attraction, attraction_pydantic, attraction_pydanticIn
from models.user import User
from services.exchange_rate import ExchangeRateService
from redis_client import redis_client
from services.http_client import cached_get
from dotenv import load_dotenv

# Load .env before using os.getenv
load_dotenv() 

HEADERS = {
    "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
    "x-rapidapi-host": os.getenv("RAPID_API_HOST")
}

# Limit concurrent API calls to avoid hitting 429 rate limit
semaphore = asyncio.Semaphore(3)
CACHE_TTL = 86400  # 24 hours


async def get_attraction_autocomplete(client: httpx.AsyncClient, city_name: str):
    """Get attraction location ID by city name (cached)."""
    cache_key = f"attraction_autocomplete:{city_name.lower()}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    async with semaphore:
        url = os.getenv("ATTRACTION_AUTO_COMPLETE_URL")
        params = {"query": city_name}
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    products = data.get("data", {}).get("products")
    if not products:
        return None

    result = products[0]["id"]
    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


async def get_attractions_search(client: httpx.AsyncClient, attraction_id: str, arrival_date: str, departure_date: str):
    """Search attractions by location ID and date range (cached)."""
    cache_key = f"attraction_search:{attraction_id}:{arrival_date}:{departure_date}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    async with semaphore:
        url = os.getenv("ATTRACTION_SEARCH_URL")
        params = {"id": attraction_id, "startDate": arrival_date, "endDate": departure_date}
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    result = data.get("data", {})
    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


async def get_availability_calendar(client: httpx.AsyncClient, attraction_id: str):
    """Get attraction availability calendar (cached)."""
    cache_key = f"availability_calendar:{attraction_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    async with semaphore:
        url = os.getenv("ATTRACTION_AVAILABILITY_CALENDAR_URL")
        params = {"id": attraction_id}
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    result = data.get("data", [])
    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


async def get_availability(client: httpx.AsyncClient, attraction_id: str, attraction_date: str):
    """Get attraction availability for a specific date (cached)."""
    cache_key = f"availability:{attraction_id}:{attraction_date}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    async with semaphore:
        url = os.getenv("ATTRACTION_AVAILABILITY_URL")
        params = {"id": attraction_id, "date": attraction_date}
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    result = data.get("data", [])
    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


async def fetch_availability_data(client: httpx.AsyncClient, attraction_id: str, attraction_date: str):
    """Fetch both availability calendar and available times for an attraction."""
    calendar_data, availability_data = await asyncio.gather(
        get_availability_calendar(client, attraction_id),
        get_availability(client, attraction_id, attraction_date)
    )

    available_dates = [
        {"availability_date": cal.get("date")}
        for cal in calendar_data
        if cal.get("available") != "false"
    ]

    available_times = [
        {"start_at": avail.get("start")}
        for avail in availability_data
    ]

    return available_dates, available_times


async def get_attraction_detail(slug: str):
    """Get full attraction description using its slug (cached)."""
    if not slug:
        return None

    cache_key = f"attraction_detail:{slug}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    async with semaphore:
        url = os.getenv("ATTRACTION_DETAIL_URL")
        params = {"slug": slug}
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    description = data.get("data", {}).get("description")
    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(description))
    return description


async def build_attractions(client: httpx.AsyncClient, attractions: dict, attraction_date: str):
    """Build detailed attractions data including availability and description."""
    found_attractions = []
    tasks = []

    # Get exchange rate data once
    exchange_data = await ExchangeRateService.get_rates()
    base_currency_code = exchange_data.get("base_currency", "BHD")
    base_currency_date = exchange_data.get("base_currency_date", "")

    # Fetch availability for all attractions in parallel
    for attraction in attractions.get("products", []):
        attr_id = attraction.get("id")
        tasks.append(fetch_availability_data(client, attr_id, attraction_date))

    availability_results = await asyncio.gather(*tasks)

    # Fetch descriptions in parallel
    detail_tasks = [
        get_attraction_detail(attraction.get("slug"))
        for attraction in attractions.get("products", [])
    ]
    descriptions = await asyncio.gather(*detail_tasks)

    # Build final attractions list
    for idx, (attraction, (available_dates, available_times)) in enumerate(
        zip(attractions.get("products", []), availability_results)
    ):
        price = attraction.get("representativePrice", {}).get("chargeAmount")
        currency = attraction.get("representativePrice", {}).get("currency", "USD")

        price_in_bhd = None
        if price is not None:
            price_in_bhd = await ExchangeRateService.convert_to_bhd(price, currency)



            # primaryPhoto:small:"https://q-xx

        attraction_info = {
            "attraction_id": attraction.get("id"),
            "attraction_name": attraction.get("name"),
            "allReviewsCount": (attraction.get("reviewsStats") or {}).get("allReviewsCount"),
            "percentageReview": (attraction.get("reviewsStats") or {}).get("percentage"),
            "averageReview": (attraction.get("numericReviewsStats") or {}).get("average"),
            "totalReview": (attraction.get("numericReviewsStats") or {}).get("total"),
            "allReviewsCount": (attraction.get("reviewsStats") or {}).get("allReviewsCount"),
            "attractionPhoto": (attraction.get("primaryPhoto") or {}).get("small"),
            "attraction_description": descriptions[idx],
            "attraction_price": price_in_bhd,
            "currency": "BHD",
            "base_currency": base_currency_code,
            "base_currency_date": base_currency_date,
            "available_date": available_dates,
            "attraction_daily_timing": available_times
        }
        found_attractions.append(attraction_info)

    return found_attractions




attractionIn=attraction_pydanticIn
async def post_attraction_service(attraction_info:attractionIn, current_user: User):  
    
    attraction_obj = await Attraction.create(
        attraction_name = attraction_info.attraction_name,
        attraction_description=attraction_info.attraction_name,
        attraction_price= attraction_info.attraction_name,
        attraction_availability_date= attraction_info.attraction_name,
        attraction_average_review=attraction_info.attraction_name,
        attraction_total_review=attraction_info.attraction_name,
        attraction_photo=attraction_info.attraction_name,
        attraction_daily_timing= attraction_info.attraction_name,
        related_user_id=current_user.id
    )
    return {
        "status": "Ok",
        "data": await attraction_pydantic.from_tortoise_orm(attraction_obj)
    }

async def get_all_attractions_service(current_user: User):
    get_all_attractions_res = await attraction_pydantic.from_queryset(
        Attraction.filter(related_user=current_user.id)  
    )
    if not get_all_attractions_res:
        raise HTTPException(status_code=404, detail="No attractions found for this user")
    return {"status": "Ok", "data": get_all_attractions_res}
