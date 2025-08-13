# ===== list hotels by city =====
import asyncio, httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from auth import get_current_user
from cors import init_cors
from database import init_db
from models.user import User, user_pydanticIn
from services.attractions import build_attractions, get_attraction_autocomplete, get_attractions_search
from services.authentication import login_service, register_service
from services.exchange_rate import ExchangeRateService
from services.flights import get_flights
from services.general import get_weather_service
from services.hotels import build_hotel_info, get_hotel_reviews, get_hotels_data, get_location_id
from services.users import delete_user_service, get_all_users_service, get_user_by_id_service, update_user_service

app = FastAPI()
init_db(app)
init_cors(app)


@app.get('/')
def index():
    return{"Msg" : "go to /docs for the API documentations"}


#===== Test security ======
@app.get("/users/profile")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name
    }


# ===== Login =====
@app.post("/auth/login", tags=["Auth"], summary="Login to get JWT token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return await login_service(form_data)


# ===== Register =====
@app.post('/auth/register', tags=["Auth"], summary="Register new user")
async def register(user_info: user_pydanticIn):
    return await register_service(user_info)


# ===== List all users =====
@app.get('/user', tags=["Users"], summary="List all users")
async def get_all_users(current_user: User = Depends(get_current_user)):
    return await get_all_users_service(current_user)

# ===== List a user by ID =====
@app.get('/user/{user_id}', tags=["Users"], summary="List a user by ID")
async def get_user_by_id(user_id: int, current_user: User = Depends(get_current_user)):
    return await get_user_by_id_service(user_id, current_user)

# ===== Update a user info by ID =====
@app.patch('/user/{user_id}', tags=["Users"], summary="Update a user info by ID")
async def update_user(user_id: int, update_info: user_pydanticIn, current_user: User = Depends(get_current_user)):
    return await update_user_service(user_id, update_info, current_user)

# ===== Delete a user by ID =====
@app.delete('/user/{user_id}', tags=["Users"], summary="Delete a user by ID")
async def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
    return await delete_user_service(user_id, current_user)

# test external apis

# ===== get a city weather =====
@app.get("/weather", tags=["get Weather info"])
async def get_weather(city: str = Query(..., description="City name in English")
):
    return await get_weather_service(city)


@app.get("/hotels", tags=["Get hotels"])
async def get_hotels(
    city_name: str = Query(..., description="City name"),
    arrival_date: str = Query(..., description="Arrival date YYYY-MM-DD"),
    departure_date: str = Query(..., description="Departure date YYYY-MM-DD"),
    page: int = Query(1, description="Page number", ge=1),
    sort_by: str = Query("price", description="Sort hotels by", regex="^(price: Price (low to high)|distance: Distance from city centre|class_descending: Property rating (high to low)|popularity: Top picks for families|bayesian_review_score: Guest review score)$"),

):
    async with httpx.AsyncClient(timeout=30) as client:
        location_id = await get_location_id(city_name, client)
        if not location_id:
            raise HTTPException(status_code=404, detail="City not found")

        hotels = await get_hotels_data(location_id, arrival_date, departure_date, client, page, sort_by)

        rates_data = await ExchangeRateService.get_rates()
        base_currency_code = rates_data.get("base_currency", "BHD")
        base_currency_date = rates_data.get("base_currency_date", 0)

        review_tasks = [get_hotel_reviews(hotel["id"], client) for hotel in hotels]
        reviews_list = await asyncio.gather(*review_tasks)

        hotel_infos = []
        for hotel, review_scores in zip(hotels, reviews_list):
            info = await build_hotel_info(
                hotel, review_scores, base_currency_code, base_currency_date
            )
            hotel_infos.append(info)

        return {
            "status": "Ok",
            "base_currency": base_currency_code,
            "base_currency_date": base_currency_date,
            "currency": "BHD",
            "data": hotel_infos
        }





# ===== list attractions by city with pagination =====
@app.get("/attraction", tags=["Get Attractions info (New test)"])
async def get_attraction(
    city_name: str = Query(..., description="City name for attraction search"),
    arrival_date: str = Query(..., description="Arrival date in YYYY-MM-DD format"),
    departure_date: str = Query(..., description="Departure date in YYYY-MM-DD format"),
    attraction_date: str = Query(..., description="Attraction date in YYYY-MM-DD format"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Number of results per page", ge=1, le=50),
):
    async with httpx.AsyncClient(timeout=30) as client:
        # Get attraction location ID (cached)
        attraction_id = await get_attraction_autocomplete(client, city_name)
        if not attraction_id:
            raise HTTPException(status_code=404, detail="No attraction found for the city")

        # Get attractions list (cached)
        attractions_data = await get_attractions_search(client, attraction_id, arrival_date, departure_date)
        if not attractions_data or "products" not in attractions_data:
            return {"status": "No attractions found", "data": []}

        total_results = len(attractions_data["products"])

        # Pagination logic
        start_index = (page - 1) * limit
        end_index = start_index + limit
        attractions_data["products"] = attractions_data["products"][start_index:end_index]

        # Get exchange rate info once (cached for 24h)
        exchange_data = await ExchangeRateService.get_rates()
        base_currency_code = exchange_data.get("base_currency", "BHD")
        base_currency_date = exchange_data.get("base_currency_date", 0)

        # Build attractions data (availability cached + semaphore to prevent 429)
        found_attractions = await build_attractions(client, attractions_data, attraction_date)

    return {
        "status": "Ok",
        "page": page,
        "limit": limit,
        "total": total_results,
        "base_currency": base_currency_code,
        "base_currency_date": base_currency_date,
        "data": found_attractions
    }


# ===== list flights by city with pagination =====
@app.get("/flight", tags=["Get flights info(New test)"])
async def flight(
    city_name: str = Query(..., description="City name for arrival airport search"),
    arrival_date: str = Query(..., description="Arrival date in YYYY-MM-DD format"),
    departure_date: str = Query(..., description="Departure date in YYYY-MM-DD format"),
    departure_city_name: str = Query(..., description="Departure city name"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Number of results per page", ge=1, le=50),
):
    # Get exchange rate info once (cached for 24h)
    exchange_data = await ExchangeRateService.get_rates()
    base_currency_code = exchange_data.get("base_currency", "BHD")
    base_currency_date = exchange_data.get("base_currency_date", 0)

    # Get flights data
    flights = await get_flights(city_name, arrival_date, departure_date, departure_city_name)

    total_results = len(flights)

    # Pagination logic
    start_index = (page - 1) * limit
    end_index = start_index + limit
    flights = flights[start_index:end_index]

    return {
        "status": "Ok",
        "page": page,
        "limit": limit,
        "total": total_results,
        "base_currency": base_currency_code,
        "base_currency_date": base_currency_date,
        "data": flights
    }
