import httpx, os
from fastapi import HTTPException
from dotenv import load_dotenv

# Load .env before using os.getenv
load_dotenv() 

async def get_weather_service(city: str):
    params = {
        "key": os.getenv("WEATHER_API_KEY"),
        "q": city,
        "aqi": "no"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(os.getenv("WEATHER_API_URL"), params=params)
            res.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Error fetching weather data")
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Weather service not reachable")

    data = res.json()
    return {
        "city": data["location"]["name"],
        "country": data["location"]["country"],
        "temperature": data["current"]["temp_c"],
        "weather": data["current"]["condition"]["text"]
    }
