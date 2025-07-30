from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx, requests, os
from tortoise.contrib.fastapi import register_tortoise
from models.models import (supplier_pydantic, supplier_pydanticIn, Supplier)
from dotenv import load_dotenv
from models.user import User, user_pydanticIn, user_pydantic
from typing import List, Optional, Type
from datetime import datetime, timedelta
load_dotenv()

api_key = os.getenv("AMADEUS_API_KEY")
api_secret = os.getenv("AMADEUS_API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")



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

@app.get("/cities", tags=["Get City info"])
async def get_cities(keyword: str):
    url = f"https://test.api.amadeus.com/v1/reference-data/locations/cities?keyword={keyword}"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        data= response.json()
        city_data = data["data"][0] if data.get("data") else None
        if not city_data:
            return {"error": "No city data found"}
        return {
            "city":city_data["name"],
            "countryCode":city_data["address"]["countryCode"],
            "latitude":city_data["geoCode"]["latitude"],
            "longitude":city_data["geoCode"]["longitude"],
        }

@app.get("/hotels", tags=["Get Hotel info"])
async def get_hotels(city_code: str = Query(..., description="IATA city code (3 letters)"), ratings: Optional[List[int]] = Query(None, description="Filter by star ratings (1-5)")):
    params = {
        "cityCode": city_code,
        "ratings": ",".join(map(str, ratings)) if ratings else None,
    }
    params = {k: v for k, v in params.items() if v is not None}
    headers = {"Authorization": f"Bearer {access_token}"}


    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city",
             headers=headers,
                params=params
            )
        response.raise_for_status()
        data = response.json()    
    
    # url = f"https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city?cityCode={city_code}&ratings={ratings}"

    # headers = {
    #     "Authorization": f"Bearer {access_token}"
    # }
    
    # async with httpx.AsyncClient() as client:
    #     response = await client.get(url, headers=headers)
    #     hotel_data= response.json().get("data",[]) 
    #     print(hotel_data)
        hotels = []
        # for hotel in hotel_data:
        #     hotels.append({
        #         "iataCode": hotel["iataCode"],
        #         "latitude": hotel["geoCode"]["latitude"],
        #         "longitude": hotel["geoCode"]["longitude"],
        #         "countryCode": hotel["address"]["countryCode"],
        #         "postalCode":hotel["address"]["postalCode"],
        #         "cityName":hotel["address"]["cityName"],
        #         "address":hotel["address"]["lines"],
        #         "rating": hotel["rating"],
        #         "lastUpdate": hotel["lastUpdate"]
        # })

        for hotel in data.get("data", []):
                    hotel_info = {
                        "name": hotel.get("name"),
                        "iataCode": hotel.get("iataCode"),
                        "rating": hotel.get("rating"),

                        "latitude": hotel.get("geoCode", {}).get("latitude"),
                        "longitude": hotel.get("geoCode", {}).get("longitude"),
                        "address": {
                                "lines": hotel.get("address", {}).get("lines"),
                                "city": hotel.get("address", {}).get("cityName"),
                                "postalCode": hotel.get("address", {}).get("postalCode"),
                                "country": hotel.get("address", {}).get("countryCode")

                        },
                        "lastUpdate": hotel.get("lastUpdate")
                    }
                    hotels.append(hotel_info)
    return {"count": len(hotels), "hotels": hotels}

    # return JSONResponse(content={"hotels": hotels})


@app.get("/restaurants", tags=["Get Restaurant info"])
async def get_hotels(city: str = Query(..., description="City name")):

    url = "https://tripadvisor16.p.rapidapi.com/api/v1/restaurant/searchLocation"

    querystring = {"query":f"{city}"}

    headers = {
        "x-rapidapi-key": "5426608891msh579aed380d1e444p1abeabjsncba767320ab6",
        "x-rapidapi-host": "tripadvisor16.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    return {"status": "Ok", "data": response.json()}


@app.get("/Hotels", tags=["Get Hotels info"])
async def get_hotels(city_name: str = Query(None, description="City name for hotel search"),
    adults: str = Query(None,description="Number of adult guests"),
    children_age: str = Query(None, description="Comma-separated list of children's ages (0-17)"),
    room_qty: str = Query(None, description="Number of rooms needed"),
    arrival_date: str = Query(None, description="Arrival date in YYYY-MM-DD format"),
    departure_date : str = Query(None, description="Departure date in YYYY-MM-DD format"),
    price_min: str = Query(None, description="Minimum price for a night"),
    price_max: str = Query(None, description="Maximum price for a night")
    ):
    search_destination_url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"


    get_search_hotel_url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"


    headers = {
        "x-rapidapi-key": "5426608891msh579aed380d1e444p1abeabjsncba767320ab6",
        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
    }
    search_destination_querystring = {"query":f"{city_name}"}



    async with httpx.AsyncClient() as client:
        search_destination_response = await  client.get(search_destination_url, headers=headers, params=search_destination_querystring)
        dest_data = search_destination_response.json()
        print(dest_data)
        dest_id = dest_data["data"][1]["dest_id"]
        print(dest_id)
        get_search_hotel_querystring = {"dest_id":dest_id,"search_type":"CITY","adults":adults,"children_age":children_age,"room_qty":room_qty,
                                   "arrival_date": arrival_date,"departure_date": departure_date,"price_min":price_min,"price_max":price_max,"currency_code":"BHD"}
        get_hotel_search_response = await client.get(get_search_hotel_url, headers=headers, params=get_search_hotel_querystring)

    return {"status": "Ok", "data": get_hotel_search_response.json()}

    


register_tortoise(
    app,
     db_url="sqlite://database.sqlite3",
     modules={"models": ["models.models","models.user","models.trips","models.preferences"]},
     generate_schemas=True,
     add_exception_handlers=True,
)
