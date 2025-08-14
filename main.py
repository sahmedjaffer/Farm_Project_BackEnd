from fastapi.responses import RedirectResponse
import asyncio, httpx
from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from config.auth import get_current_user
from config.cors import init_cors
from config.database import init_db
from models.user import User, user_pydanticIn
from models.hotel import hotel_pydanticIn
from models.flight import flight_pydanticIn
from models.attraction import attraction_pydanticIn
from services.attractions import (
    build_attractions, get_all_attractions_service, get_attraction_autocomplete,
    get_attractions_search, post_attraction_service
)
from services.authentication import (
    OAuth2PasswordRequestFormCustom, login_service, register_service
)
from services.exchange_rate import ExchangeRateService
from services.flights import get_all_flights_service, get_flights, post_flight_service
from services.general import get_weather_service
from services.hotels import (
     assemble_hotel_info, get_all_hotels_service, get_hotel_full_detail, get_hotel_reviews,
    get_hotels_data, get_location_id, post_hotel_service
)
from services.users import (
    delete_user_service, get_all_users_service,
    get_user_by_id_service, update_user_service
)

app = FastAPI()

# Initialize database and CORS settings
init_db(app)
init_cors(app)

# Redirect root URL to Swagger docs UI
@app.get('/')
def index():
    return RedirectResponse(url="/docs")


# ===== User profile endpoint (secured) =====
@app.get("/users/profile")
async def read_users_me(current_user: User = Depends(get_current_user)):
    # Returns the currently logged-in user's basic info
    return {
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name
    }


# ===== Login endpoint =====
@app.post("/auth/login", tags=["Auth"], summary="Login to get JWT token")
async def login(form_data: OAuth2PasswordRequestFormCustom = Depends()):
    # Handles login and returns JWT token if credentials are valid
    return await login_service(form_data)


# ===== Register endpoint =====
userIn = user_pydanticIn
@app.post('/auth/register', tags=["Auth"], summary="Register new user")
async def register(user_info: userIn):
    # Registers a new user
    return await register_service(user_info)


# ===== List all users (secured) =====
@app.get('/user', tags=["Users"], summary="List all users")
async def get_all_users(current_user: User = Depends(get_current_user)):
    # Returns a list of all users (only accessible by authenticated users)
    return await get_all_users_service(current_user)


# ===== Get user by ID (secured) =====
@app.get('/auth/user/{user_id}', tags=["Auth"], summary="List a user by ID")
async def get_user_by_id(user_id: UUID, current_user: User = Depends(get_current_user)):
    # Returns user info by UUID
    return await get_user_by_id_service(user_id, current_user)


# ===== Update user info by ID (secured) =====
@app.patch('/auth/user/{user_id}', tags=["Auth"], summary="Update a user info by ID")
async def update_user(user_id: UUID, update_info: userIn, current_user: User = Depends(get_current_user)):
    # Updates specified user fields
    return await update_user_service(user_id, update_info, current_user)


# ===== Delete user by ID (secured) =====
@app.delete('/auth/user/{user_id}', tags=["Auth"], summary="Delete a user by ID")
async def delete_user(user_id: UUID, current_user: User = Depends(get_current_user)):
    # Deletes the specified user from the database
    return await delete_user_service(user_id, current_user)


# ===== Get weather data for a city =====
@app.get("/weather", tags=["Weather"], summary="Find the weather")
async def get_weather(city: str):
    # Fetches current weather info for the requested city from an external API
    return await get_weather_service(city)

# ===== Search hotels =====
@app.get("/hotel", tags=["Hotel"], summary="Find hotels")
async def get_hotels(
    city_name: str = Query(..., description="City name"),
    arrival_date: str = Query(..., description="Arrival date YYYY-MM-DD"),
    departure_date: str = Query(..., description="Departure date YYYY-MM-DD"),
    page: int = Query(1, description="Page number", ge=1),
    sort_by: str = Query("price", description="Sort hotels by", regex="^(price|review_score|distance|upsort_bh|popularity|class_descending|class_ascending|bayesian_review_score)$"),
):
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Get location ID
        location_id = await get_location_id(city_name, client)
        if not location_id:
            raise HTTPException(status_code=404, detail="City not found")

        # Fetch hotels
        hotels = await get_hotels_data(location_id, arrival_date, departure_date, client, page, sort_by)
        if not hotels:
            return {"status": "Ok", "data": []}

        # Fetch exchange rates
        rates_data = await ExchangeRateService.get_rates()
        base_currency_code = rates_data.get("base_currency", "BHD")
        base_currency_date = rates_data.get("base_currency_date", 0)

        # Prepare concurrent tasks for reviews and full details (including photos)
        review_tasks = [get_hotel_reviews(hotel["id"], client) for hotel in hotels]
        full_detail_tasks = [get_hotel_full_detail(hotel["id"], client, arrival_date, departure_date) for hotel in hotels]

        # Run all tasks concurrently
        reviews_list, full_details_list = await asyncio.gather(
            asyncio.gather(*review_tasks),
            asyncio.gather(*full_detail_tasks)
        )

        # Build hotel info
        hotel_infos = []
        for hotel, review_scores, full_details in zip(hotels, reviews_list, full_details_list):
            hotel_booking_url = full_details.get("hotel_booking_url")
            hotel_address = full_details.get("hotel_address")
            hotel_photo_url = full_details.get("hotel_photo_url")

            info = await assemble_hotel_info(
                hotel,
                review_scores,
                hotel_booking_url,
                hotel_photo_url,
                hotel_address,
                base_currency_code,
                base_currency_date
            )
            hotel_infos.append(info)

        return hotel_infos



hotelIn = hotel_pydanticIn

# ===== Save user-selected hotel =====
@app.post('/hotel', tags=["Hotel"], summary="Save user hotel")
async def saveHotel(hotel_info: hotelIn, current_user: User = Depends(get_current_user)):
    # Saves hotel selection linked to the current user
    return await post_hotel_service(hotel_info, current_user)


# ===== List all hotels saved by the current user =====
@app.get("/user/{user_id}/hotels", tags=["Hotel"], summary="List all user's hotels")
async def get_all_hotels(current_user: User = Depends(get_current_user)):
    # Fetches all hotels saved by the authenticated user
    return await get_all_hotels_service(current_user)


# ===== List attractions by city =====
@app.get("/attraction", tags=["Attraction"], summary="Find attractions")
async def get_attraction(
    city_name: str = Query(..., description="City name for attraction search"),
    arrival_date: str = Query(..., description="Arrival date YYYY-MM-DD format"),
    departure_date: str = Query(..., description="Departure date YYYY-MM-DD format"),
):
    # Retrieves attractions for a city in the specified date range using external APIs,
    # includes caching, rate limiting, and price conversion

    limit = 10
    attraction_date = arrival_date
    async with httpx.AsyncClient(timeout=30) as client:
        attraction_id = await get_attraction_autocomplete(client, city_name)
        if not attraction_id:
            raise HTTPException(status_code=404, detail="No attraction found for the city")

        attractions_data = await get_attractions_search(client, attraction_id, arrival_date, departure_date)
        if not attractions_data or "products" not in attractions_data:
            return {"status": "No attractions found", "data": []}

        total_results = len(attractions_data["products"])

        exchange_data = await ExchangeRateService.get_rates()
        base_currency_code = exchange_data.get("base_currency", "BHD")
        base_currency_date = exchange_data.get("base_currency_date", 0)

        # Build full attraction info including availability (with caching + semaphore)
        found_attractions = await build_attractions(client, attractions_data, attraction_date)

    return {
        "status": "Ok",
        "limit": limit,
        "total": total_results,
        "base_currency": base_currency_code,
        "base_currency_date": base_currency_date,
        "data": found_attractions
    }


attractionIn = attraction_pydanticIn

# ===== Save user-selected attraction =====
@app.post('/attraction', tags=["Attraction"], summary="Save user attraction")
async def saveAttraction(attraction_info: attractionIn, current_user: User = Depends(get_current_user)):
    # Saves attraction selection linked to the current user
    return await post_attraction_service(attraction_info, current_user)


# ===== List all attractions saved by the current user =====
@app.get("/user/{user_id}/attraction", tags=["Attraction"], summary="List all user's Attractions")
async def get_all_attractions(current_user: User = Depends(get_current_user)):
    # Fetches all attractions saved by the authenticated user
    return await get_all_attractions_service(current_user)


# ===== List flights by city with pagination =====
@app.get("/flight", tags=["Flight"], summary="Get flights info")
async def flight(
    city_name: str = Query(..., description="City name for arrival airport search"),
    arrival_date: str = Query(..., description="Arrival date YYYY-MM-DD format"),
    departure_date: str = Query(..., description="Departure date YYYY-MM-DD format"),
    departure_city_name: str = Query(..., description="Departure city name"),

):
    # Fetches flight info between departure and arrival cities/dates,
    # applies pagination and currency conversion for pricing

    exchange_data = await ExchangeRateService.get_rates()
    base_currency_code = exchange_data.get("base_currency", "BHD")
    base_currency_date = exchange_data.get("base_currency_date", 0)

    flights = await get_flights(city_name, arrival_date, departure_date, departure_city_name)

    total_results = len(flights)

    # Pagination slicing



    return {
        "status": "Ok",
        "total": total_results,
        "base_currency": base_currency_code,
        "base_currency_date": base_currency_date,
        "data": flights
    }


flightIn = flight_pydanticIn

# ===== Save user-selected flight =====
@app.post('/flight', tags=["Flight"], summary="Save user Flight")
async def saveFlight(flight_info: flightIn, current_user: User = Depends(get_current_user)):
    # Saves flight selection linked to the current user
    return await post_flight_service(flight_info, current_user)


# ===== List all flights saved by the current user =====
@app.get("/user/{user_id}/flights", tags=["Flight"], summary="List all user's Flights")
async def get_all_flights(current_user: User = Depends(get_current_user)):
    # Fetches all flights saved by the authenticated user
    return await get_all_flights_service(current_user)