from uuid import UUID
from fastapi import Depends, HTTPException
import httpx, asyncio, json, os
from config.auth import get_current_user
from models.attraction import Attraction, attraction_pydantic, attraction_pydanticIn
from models.user import User
from services.exchange_rate import ExchangeRateService
from config.redis_client import get_redis_client
from services.http_client import cached_get
from dotenv import load_dotenv

# Load environment variables from .env file before accessing them
load_dotenv() 

# Prepare headers for API calls, using API keys from environment variables
HEADERS = {
    "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
    "x-rapidapi-host": os.getenv("RAPID_API_HOST")
}

# Limit number of concurrent API requests to 3 to avoid rate limiting (HTTP 429 errors)
semaphore = asyncio.Semaphore(3)

# Cache time-to-live (TTL) in seconds (24 hours)
CACHE_TTL = 86400  


async def get_attraction_autocomplete(client: httpx.AsyncClient, city_name: str):
    """
    Search for attraction location ID by city name, using Redis cache to avoid repeated API calls.
    """
    cache_key = f"attraction_autocomplete:{city_name.lower()}"  # Cache key based on city name
    cached = await get_redis_client().get(cache_key)  # Try to get cached result
    if cached:
        return json.loads(cached)  # Return cached data if exists

    # Use semaphore to limit concurrent API calls
    async with semaphore:
        url = os.getenv("ATTRACTION_AUTO_COMPLETE_URL")
        params = {"query": city_name}
        # Call external API with caching helper function
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    products = data.get("data", {}).get("products")
    if not products:
        return None  # No products found

    result = products[0]["id"]  # Take the first product ID as result
    # Cache the result in Redis with expiry
    await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


async def get_attractions_search(client: httpx.AsyncClient, attraction_id: str, arrival_date: str, departure_date: str):
    """
    Search for attractions by location ID and date range, with caching.
    """
    cache_key = f"attraction_search:{attraction_id}:{arrival_date}:{departure_date}"
    cached = await get_redis_client().get(cache_key)  # Check cache first
    if cached:
        return json.loads(cached)

    async with semaphore:
        url = os.getenv("ATTRACTION_SEARCH_URL")
        params = {"id": attraction_id, "startDate": arrival_date, "endDate": departure_date}
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    result = data.get("data", {})
    await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(result))  # Cache the fresh result
    return result


async def get_availability_calendar(client: httpx.AsyncClient, attraction_id: str):
    """
    Get availability calendar for a given attraction (cached).
    """
    cache_key = f"availability_calendar:{attraction_id}"
    cached = await get_redis_client().get(cache_key)
    if cached:
        return json.loads(cached)

    async with semaphore:
        url = os.getenv("ATTRACTION_AVAILABILITY_CALENDAR_URL")
        params = {"id": attraction_id}
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    result = data.get("data", [])
    await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


async def get_availability(client: httpx.AsyncClient, attraction_id: str, attraction_date: str):
    """
    Get availability information for a specific date of an attraction (cached).
    """
    cache_key = f"availability:{attraction_id}:{attraction_date}"
    cached = await get_redis_client().get(cache_key)
    if cached:
        return json.loads(cached)

    async with semaphore:
        url = os.getenv("ATTRACTION_AVAILABILITY_URL")
        params = {"id": attraction_id, "date": attraction_date}
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    result = data.get("data", [])
    await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


async def fetch_availability_data(client: httpx.AsyncClient, attraction_id: str, attraction_date: str):
    """
    Fetch availability calendar and specific date availability concurrently.
    Returns lists of available dates and available time slots.
    """
    # Fetch calendar and date availability concurrently for performance
    calendar_data, availability_data = await asyncio.gather(
        get_availability_calendar(client, attraction_id),
        get_availability(client, attraction_id, attraction_date)
    )

    # Filter available dates where "available" is not "false"
    available_dates = [
        {"availability_date": cal.get("date")}
        for cal in calendar_data
        if cal.get("available") != "false"
    ]

    # Extract available start times
    available_times = [
        {"start_at": avail.get("start")}
        for avail in availability_data
    ]

    return available_dates, available_times


async def get_attraction_detail(slug: str):
    """
    Fetch full attraction description by slug, using caching to reduce API calls.
    """
    if not slug:
        return None

    cache_key = f"attraction_detail:{slug}"
    cached = await get_redis_client().get(cache_key)
    if cached:
        return json.loads(cached)

    async with semaphore:
        url = os.getenv("ATTRACTION_DETAIL_URL")
        params = {"slug": slug}
        data = await cached_get(url, params=params, headers=HEADERS, ttl=CACHE_TTL)

    description = data.get("data", {}).get("description")
    await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(description))
    return description


async def build_attractions(client: httpx.AsyncClient, attractions: dict, attraction_date: str):
    """
    Build a detailed list of attractions with availability, descriptions, and price conversions.
    """
    found_attractions = []
    tasks = []

    # Get exchange rates once to convert all prices to BHD (Bahraini Dinar)
    exchange_data = await ExchangeRateService.get_rates()
    base_currency_code = exchange_data.get("base_currency", "BHD")
    base_currency_date = exchange_data.get("base_currency_date", "")

    # Prepare asynchronous tasks to fetch availability data for all attractions
    for attraction in attractions.get("products", []):
        attr_id = attraction.get("id")
        tasks.append(fetch_availability_data(client, attr_id, attraction_date))

    # Run all availability fetches concurrently
    availability_results = await asyncio.gather(*tasks)

    # Prepare tasks to fetch attraction descriptions concurrently
    detail_tasks = [
        get_attraction_detail(attraction.get("slug"))
        for attraction in attractions.get("products", [])
    ]
    descriptions = await asyncio.gather(*detail_tasks)

    # Combine all data to build the final list of attraction info dictionaries
    for idx, (attraction, (available_dates, available_times)) in enumerate(
        zip(attractions.get("products", []), availability_results)
    ):
        price = attraction.get("representativePrice", {}).get("chargeAmount")
        currency = attraction.get("representativePrice", {}).get("currency", "USD")

        price_in_bhd = None
        if price is not None:
            # Convert price to BHD currency
            price_in_bhd = await ExchangeRateService.convert_to_bhd(price, currency)

        attraction_info = {
            "attraction_id": attraction.get("id"),
            "attraction_name": attraction.get("name"),
            "allReviewsCount": (attraction.get("reviewsStats") or {}).get("allReviewsCount"),
            "percentageReview": (attraction.get("reviewsStats") or {}).get("percentage"),
            "averageReview": (attraction.get("numericReviewsStats") or {}).get("average"),
            "totalReview": (attraction.get("numericReviewsStats") or {}).get("total"),
            "allReviewsCount": (attraction.get("reviewsStats") or {}).get("allReviewsCount"),
            "attractionPhoto": (attraction.get("primaryPhoto") or {}).get("small"),
            "attraction_description": descriptions[idx],  # Use cached or fetched description
            "attraction_price": price_in_bhd,  # Price converted to BHD
            "currency": "BHD",
            "base_currency": base_currency_code,
            "base_currency_date": base_currency_date,
            "available_date": available_dates,
            "attraction_daily_timing": available_times
        }
        found_attractions.append(attraction_info)

    return found_attractions


# Pydantic input model for attraction data
attractionIn = attraction_pydanticIn

async def post_attraction_service(attraction_info: attractionIn, current_user: User):
    """
    Create a new attraction record in the database linked to the current user.
    """
    attraction_obj = await Attraction.create(
        attraction_name=attraction_info.attraction_name,
        attraction_description=attraction_info.attraction_description,
        attraction_price=attraction_info.attraction_price,
        attraction_availability_date=attraction_info.attraction_availability_date,
        attraction_average_review=attraction_info.attraction_average_review,
        attraction_total_review=attraction_info.attraction_total_review,
        attraction_photo=attraction_info.attraction_photo,
        attraction_daily_timing=attraction_info.attraction_daily_timing,
        related_user_id=current_user.id
    )
    # Return the newly created attraction data as Pydantic model
    return {
        "status": "Ok",
        "data": await attraction_pydantic.from_tortoise_orm(attraction_obj)
    }


async def get_all_attractions_service(current_user: User):
    """
    Retrieve all attractions related to the current user from the database.
    Raise 404 error if none found.
    """
    get_all_attractions_res = await attraction_pydantic.from_queryset(
        Attraction.filter(related_user=current_user.id)
    )
    if not get_all_attractions_res:
        raise HTTPException(status_code=404, detail="No attractions found for this user")
    return {"status": "Ok", "data": (get_all_attractions_res,current_user.id)}



async def delete_attraction_service(
    attraction_id: int,
    user_id: UUID,
    current_user: User = Depends(get_current_user)
):
    # Fetch hotel by id
    attraction = await Attraction.get_or_none(id=attraction_id)
    if not attraction:
        raise HTTPException(status_code=404, detail="Attraction not found")

    # Check ownership
    if attraction.related_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this hotel")

    # Delete hotel and get deleted count
    deleted_count = await Attraction.filter(id=attraction_id).delete()
    
    return {"status": "Ok", "deleted_count": deleted_count}
