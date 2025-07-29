from fastapi import FastAPI, HTTPException
import httpx, requests, os 
from tortoise.contrib.fastapi import register_tortoise
from models import (supplier_pydantic, supplier_pydanticIn, Supplier)
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("AMADEUS_API_KEY")
api_secret = os.getenv("AMADEUS_API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")



app = FastAPI()


@app.get('/')
def index():
    return{"Msg" : "go to /docs for the API documentations"}


# create new supplier
@app.post('/supplier')
async def add_supplier(supplier_info: supplier_pydanticIn):
    supplier_obj = await Supplier.create(**supplier_info.dict(exclude_unset=True))
    craete_supplier_res = await supplier_pydantic.from_tortoise_orm(supplier_obj)
    return {"status": "Ok", "data" : craete_supplier_res}

# list all suppliers
@app.get('/suppliers')
async def get_suppliers():
    get_all_suppliers_res = await supplier_pydantic.from_queryset(Supplier.all())
    if not get_all_suppliers_res:
        raise HTTPException(status_code=404, detail="No suppliers  found")
    return {"status": "Ok", "data": get_all_suppliers_res}

#list a supplier by id
@app.get('/supplier/{supplier_id}')
async def get_supplier(supplier_id: int):
    get_one_suppliers_res = await supplier_pydantic.from_queryset_single(
        Supplier.get(id=supplier_id)
    )
    if not get_one_suppliers_res:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"status": "Ok", "data": get_one_suppliers_res}




# test external apis

@app.get("/weather")
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

@app.get("/cities")
async def get_cities(keyword: str):
    url = f"https://test.api.amadeus.com/v1/reference-data/locations/cities?keyword={keyword}"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()








register_tortoise(
    app,
     db_url="sqlite://database.sqlite3",
     modules={"models": ["models"]},
     generate_schemas=True,
     add_exception_handlers=True,
)
