import httpx, os
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables from .env file before accessing with os.getenv
load_dotenv() 

async def get_weather_service(city: str):
    """
    Asynchronous function to get current weather data for a given city
    from an external weather API.
    """

    # Prepare query parameters for the API request
    params = {
        "key": os.getenv("WEATHER_API_KEY"),  # API key from environment variables
        "q": city,                            # City name to query weather for
        "aqi": "no"                          # Disable air quality index data
    }

    # Use an async HTTP client with a timeout of 10 seconds
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Send GET request to the weather API URL with the query parameters
            res = await client.get(os.getenv("WEATHER_API_URL"), params=params)
            # Raise exception if HTTP status is an error (4xx or 5xx)
            res.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Raise HTTPException with status code and message if API returns error response
            raise HTTPException(status_code=e.response.status_code, detail="Error fetching weather data")
        except httpx.RequestError:
            # Raise HTTPException if there was a problem connecting to the API (network issues, timeout, etc.)
            raise HTTPException(status_code=500, detail="Weather service not reachable")

    # Parse the JSON response data
    data = res.json()

    # Return selected weather details as a dictionary
    return {
        "city": data["location"]["name"],             # City name from response
        "country": data["location"]["country"],       # Country name from response
        "temperature": data["current"]["temp_c"],     # Current temperature in Celsius
        "feels_like": data["current"]["feelslike_c"], # Feels like temperature in Celsius
        "humidity": data["current"]["humidity"],      # Current humidity percentage
        "wind_kph": data["current"]["wind_kph"],      # Wind speed in kilometers per hour
        "weather": data["current"]["condition"]["text"]  # Text description of weather condition
    }
