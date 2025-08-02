from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
# import httpx, requests, os
import httpx
from tortoise.contrib.fastapi import register_tortoise
from models.models import (supplier_pydantic, supplier_pydanticIn, Supplier)
from dotenv import load_dotenv
from models.user import User, user_pydanticIn, user_pydantic
from typing import List, Optional, Type
from datetime import datetime, timedelta
load_dotenv()

# api_key = os.getenv("AMADEUS_API_KEY")
# api_secret = os.getenv("AMADEUS_API_SECRET")
# access_token = os.getenv("ACCESS_TOKEN")



app = FastAPI()


@app.get('/')
def index():
    return{"Msg" : "go to /docs for the API documentations"}


userIn = user_pydanticIn
user = user_pydantic
# create new user
@app.post('/user' , tags=["Users"], summary="Create new user")
async def add_user(user_info: userIn):
    user_obj = await User.create(**user_info.model_dump(exclude_unset=True))
    create_user_res = await user.from_tortoise_orm(user_obj)
    return {"status": "Ok", "data" : create_user_res}


# list all users
@app.get('/user' , tags=["Users"], summary="List all users")
async def get_all_users():
    get_all_users_res = await user.from_queryset(User.all())
    if not get_all_users_res:
        raise HTTPException(status_code=404, detail="No users  found")
    return {"status": "Ok", "data": get_all_users_res}

#list a user by id
@app.get('/user/{user_id}' , tags=["Users"], summary="List a user by ID")
async def get_user_by_id(user_id: int):
    get_user_by_id_res = await user.from_queryset_single(User.get(id=user_id))
    if not get_user_by_id_res:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "Ok", "data": get_user_by_id_res}



#update user by id
@app.patch('/user/{user_id}' , tags=["Users"], summary="Update a user info by ID")
async def update_user(user_id: int, update_info: userIn):
    get_update_user = await User.get(id = user_id)
    update_info = update_info.model_dump(exclude_unset=True)
    get_update_user.first_name = update_info['first_name']
    get_update_user.last_name = update_info['last_name']
    get_update_user.email = update_info['email']
    #get_update_user.hashed_password = update_info['hashed_password']
    #save updates
    get_update_user.save()
    update_user_res = user.from_tortoise_orm(get_update_user)
    return {"status": "Ok", "data": update_user_res}

#delete user by id
@app.delete('/user/{user_id}', tags=["Users"], summary="Delete a user by ID")
async def delete_user (user_id: int):
    delete_user_res = await User.get(id = user_id).delete()
    return {"status": "Ok", "data": delete_user_res}




# create new supplier
@app.post('/supplier', tags=["Suppliers"], summary="Create new supplier")
async def add_supplier(supplier_info: supplier_pydanticIn):
    supplier_obj = await Supplier.create(**supplier_info.dict(exclude_unset=True))
    craete_supplier_res = await supplier_pydantic.from_tortoise_orm(supplier_obj)
    return {"status": "Ok", "data" : craete_supplier_res}

# list all suppliers
@app.get('/supplier', tags=["Suppliers"], summary="List all suppliers")
async def get_all_suppliers():
    get_all_suppliers_res = await supplier_pydantic.from_queryset(Supplier.all())
    if not get_all_suppliers_res:
        raise HTTPException(status_code=404, detail="No suppliers  found")
    return {"status": "Ok", "data": get_all_suppliers_res}

#list a supplier by id
@app.get('/supplier/{supplier_id}', tags=["Suppliers"], summary="List a supplier by id")
async def get_one_supplier(supplier_id: int):
    get_one_suppliers_res = await supplier_pydantic.from_queryset_single(Supplier.get(id=supplier_id))
    if not get_one_suppliers_res:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"status": "Ok", "data": get_one_suppliers_res}

@app.patch('/supplier/{supplier_id}', tags=["Suppliers"], summary="Update a supplier by id")
async def update_supplier(supplier_id: int, update_info: supplier_pydanticIn):
    get_update_supplier = await Supplier.get(id=supplier_id)
    if not get_update_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    update_info = update_info.dict(exclude_unset=True)
    for field, value in update_info.items():
        setattr(get_update_supplier, field, value)


    # get_update_supplier.name = update_info['name']
    # get_update_supplier.company = update_info.company
    # get_update_supplier.email = update_info.email
    # get_update_supplier.phone = update_info.phone
    #save updates
    await get_update_supplier.save()
    update_supplier_res = await supplier_pydantic.from_tortoise_orm(get_update_supplier)
    return {"status": "Ok", "data": update_supplier_res}


@app.delete('/supplier/{supplier_id}', tags=["Suppliers"], summary="Delete a supplier by id")
async def delete_supplier (supplier_id: int):
    get_delete_supplier = await Supplier.get(id = supplier_id).delete()
    return {"status": "Ok", "data": get_delete_supplier}


# test external apis

@app.get("/weather", tags=["get Weather info"])
def get_weather(city: str):
    res = requests.get(
        f"http://api.weatherapi.com/v1/current.json?key=47793dce3b9b4faa9f4132058251407&q={city}&aqi=no"
    )
    data = res.json()
    return {
        "city": data["location"]["name"],
        "country": data["location"]["country"],
        "temperature": data["current"]["temp_c"],
        "weather": data["current"]["condition"]["text"]
    }

@app.get("/Hotels", tags=["Get Hotels info(New test)"])
async def get_hotels(city_name: str = Query(None, description="City name for hotel search"),
    arrival_date: str = Query(None, description="Arrival date in YYYY-MM-DD format"),
    departure_date : str = Query(None, description="Departure date in YYYY-MM-DD format"),

    ):

    # to find hotel by location and some info
    hotel_auto_complete_url = "https://booking-com18.p.rapidapi.com/stays/auto-complete"
    hotel_search_url = "https://booking-com18.p.rapidapi.com/stays/search"
    hotel_review_scores_url = "https://booking-com18.p.rapidapi.com/stays/review-scores"
    hotel_auto_complete_querystring = {"query":f"{city_name}"}

    #flight API's

    # flight_auto_complete_url = "https://booking-com18.p.rapidapi.com/flights/v2/auto-complete"
    # flight_roundtrip_url = "https://booking-com18.p.rapidapi.com/flights/v2/min-price-roundtrip"
    # flight_auto_complete_querystring = {"query":f"{city_name}"}
    # flight_roundtrip_querystring= {"departId":f"{depart_id}","arrivalId":f"{arrival_id}","departDate":f"{arrival_date}","returnDate":f"{departure_date}"}

    headers = {
        "x-rapidapi-key": "5426608891msh579aed380d1e444p1abeabjsncba767320ab6",
        "x-rapidapi-host": "booking-com18.p.rapidapi.com"
    }

    async with httpx.AsyncClient() as client:
        # api to find the destination
        hotel_auto_complete_response = await  client.get(hotel_auto_complete_url, headers=headers, params=hotel_auto_complete_querystring)
        hotel_auto_complete_data = hotel_auto_complete_response.json()
        location_id = hotel_auto_complete_data["data"][0]["id"]
        location_name=hotel_auto_complete_data["data"][0]["name"]
        location_country=hotel_auto_complete_data["data"][0]["country"]

        # api to search for the hotels
        hotel_search_querystring = {"locationId":f"{location_id}" ,"checkinDate":f"{arrival_date}","checkoutDate":f"{departure_date}","sortBy":"price","units":"metric","temperature":"c", "currencyCode":"BHD"}
        hotel_search_response = await client.get(hotel_search_url, headers=headers, params= hotel_search_querystring)
        hotel_search_data= hotel_search_response.json()
        hotels_data = hotel_search_data.get("data", [])
        if not hotels_data:
            return {"status": "No hotels found", "data": []}

        found_hotels=[]
        for hotel in hotels_data:
                    hotel_id = hotel.get("id")
                    print(hotel_id)
                    hotel_review_scores_querystring = {"hotelId":f"{hotel_id}"}
                    hotel_review_scores_response= await client.get(hotel_review_scores_url, headers=headers, params= hotel_review_scores_querystring)
                    hotel_review_scores_data= hotel_review_scores_response.json()
                    hotel_info = {
                        "hotel_id": hotel.get("id"),
                        "hotel_name": hotel.get("name"),
                        "review_scoreWord": hotel.get("reviewScoreWord"),
                        "review_score": hotel.get("reviewScore"),
                        "gross_price": hotel.get("priceBreakdown", {}).get("grossPrice", {}).get("value"),
                        "check_in":{
                                       "from": hotel.get("checkin", {}).get("fromTime", {}),
                                       "until":hotel.get("checkin", {}).get("untilTime", {}),
                        },
                        "check_out":{
                                       "from": hotel.get("checkout", {}).get("fromTime", {}),
                                       "until":hotel.get("checkout", {}).get("untilTime", {}),
                        },
                        "score": {                        
                            "Wonderful":{
                                 "percent": hotel_review_scores_data["data"]["score_percentage"][0]["percent"],
                                 "count": hotel_review_scores_data["data"]["score_percentage"][0]["count"],
                                 },
                            "Good": {
                                 "percent": hotel_review_scores_data["data"]["score_percentage"][1]["percent"],
                                 "count": hotel_review_scores_data["data"]["score_percentage"][1]["count"],
                                 },
                            "Okay":{
                                 "percent": hotel_review_scores_data["data"]["score_percentage"][2]["percent"],
                                 "count": hotel_review_scores_data["data"]["score_percentage"][2]["count"],
                                 },
                            "Poor":{
                                 "percent": hotel_review_scores_data["data"]["score_percentage"][3]["percent"],
                                 "count": hotel_review_scores_data["data"]["score_percentage"][3]["count"],
                                 },
                            "Very Poor":{
                                 "percent": hotel_review_scores_data["data"]["score_percentage"][4]["percent"],
                                 "count": hotel_review_scores_data["data"]["score_percentage"][4]["count"],
                                 },}
                    }
                    found_hotels.append(hotel_info)
    return {"status": "Ok", "data": found_hotels}



@app.get("/attraction", tags=["Get Attractions info(New test)"])
async def get_hotels(city_name: str = Query(None, description="City name for hotel search"),
    arrival_date: str = Query(None, description="Arrival date in YYYY-MM-DD format"),
    departure_date : str = Query(None, description="Departure date in YYYY-MM-DD format"),
    attraction_date: str = Query(None, description="Attraction date in YYYY-MM-DD format"),
    ):
    #attraction API's
    attraction_auto_complete_url = "https://booking-com18.p.rapidapi.com/attraction/auto-complete"
    attraction_search_url = "https://booking-com18.p.rapidapi.com/attraction/search"
    attraction_auto_complete_querystring = {"query":f"{city_name}"}
    headers = {
        "x-rapidapi-key": "5426608891msh579aed380d1e444p1abeabjsncba767320ab6",
        "x-rapidapi-host": "booking-com18.p.rapidapi.com"
    }
    async with httpx.AsyncClient() as client:
        # api to find the attraction
        attraction_auto_complete_response = await  client.get(attraction_auto_complete_url, headers=headers, params=attraction_auto_complete_querystring)
        attraction_auto_complete_data = attraction_auto_complete_response.json()
        attraction_id= attraction_auto_complete_data["data"]["products"][0]["id"]
        attraction_search_querystring = {"id":f"{attraction_id}","startDate":f"{arrival_date}","endDate":f"{departure_date}"}
        attraction_search_response = await  client.get(attraction_search_url, headers=headers, params=attraction_search_querystring)
        attraction_search_data = attraction_search_response.json()
        attractions_data = attraction_search_data.get("data", [])
        if not attractions_data:
            return {"status": "No attractions found", "data": []}
        found_attractions = []
        if attractions_data and "products" in attractions_data:
            attraction_availability_querystring = {"id":f"{attraction_id}","date":f"{attraction_date}"}
            
            for attraction in attractions_data["products"]:
                attraction_info = {
                    "attraction_id":(id== attraction.get("id")),
                    "attraction_name": attraction.get("name"),
                    "attraction_short_description": attraction.get("shortDescription"),
                    "attraction_price": attraction.get("representativePrice", {}).get("chargeAmount"),
                    "currency": attraction.get("representativePrice", {}).get("currency", "USD")
                }
                found_attractions.append(attraction_info)
                print(attraction_info)
            # found_attraction.append(attraction_info)
    return {"status": "Ok", "data": found_attractions}

app.get("/flight", tags=["Get flights info(New test)"])
async def get_hotels(city_name: str = Query(None, description="City name for hotel search"),
    arrival_date: str = Query(None, description="Arrival date in YYYY-MM-DD format"),
    departure_date : str = Query(None, description="Departure date in YYYY-MM-DD format"),
    departure_city_name: str = Query(None, description="departure city"),
    ):
    headers = {
        "x-rapidapi-key": "5426608891msh579aed380d1e444p1abeabjsncba767320ab6",
        "x-rapidapi-host": "booking-com18.p.rapidapi.com"
    }
        #flight API's

    flight_auto_complete_url = "https://booking-com18.p.rapidapi.com/flights/v2/auto-complete"
    flight_auto_complete_querystring = {"query":f"{city_name}"}
    async with httpx.AsyncClient() as client:

        flight_auto_complete_response = await  client.get(flight_auto_complete_url, headers=headers, params=flight_auto_complete_querystring)
        flight_auto_complete_data = flight_auto_complete_response.json()
        flight_auto_data = flight_auto_complete_data.get("data", [])
        for airport in flight_auto_data:
            type = airport.get("type")
            if type == "AIRPORT":
                airport_info = {
                    "airport_name": airport.get("name"),
                    "airport_code": airport.get("code"),
                    "city_name": airport.get("cityName"),
                    "country_name": airport.get("countryName"),
                    "distance_to_city": airport.get("distanceToCity").get("value")
                } 




    flight_roundtrip_querystring= {"departId":f"{depart_id}","arrivalId":f"{arrival_id}","departDate":f"{arrival_date}","returnDate":f"{departure_date}"}
    flight_roundtrip_url = "https://booking-com18.p.rapidapi.com/flights/v2/min-price-roundtrip"




register_tortoise(
    app,
     db_url="sqlite://database.sqlite3",
     modules={"models": ["models.models","models.user","models.trips","models.preferences"]},
     generate_schemas=True,
     add_exception_handlers=True,
)
