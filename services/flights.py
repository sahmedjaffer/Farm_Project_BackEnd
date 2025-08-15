import httpx, asyncio, json, os
from fastapi import HTTPException
from typing import Dict, Any
from models.user import User
from models.flight import Flight, flight_pydantic, flight_pydanticIn
from services.exchange_rate import ExchangeRateService
from config.redis_client import get_redis_client
from services.http_client import cached_get 
from dotenv import load_dotenv

# Load environment variables from .env file before using os.getenv
load_dotenv() 

# API headers with keys loaded from environment variables
HEADERS = {
    "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
    "x-rapidapi-host": os.getenv("RAPID_API_HOST")
}

# Timeout for HTTP requests (seconds)
TIMEOUT = 30.0

# Cache time-to-live (seconds) and concurrency semaphore for rate limiting
CACHE_TTL = 86400  # cache results for 24 hours
semaphore = asyncio.Semaphore(3)  # allow max 3 concurrent API calls


async def get_airport_info(client: httpx.AsyncClient, city: str):
    """
    Fetch airport info for a city, cached in Redis.
    Returns a tuple: (first airport code found, list of airports in city)
    """
    cache_key = f"airport_info:{city}"
    cached = await get_redis_client().get(cache_key)
    if cached:
        # Return cached airport info if available
        return json.loads(cached)

    # If no cache, call external API to autocomplete airport for city
    resp = await client.get(os.getenv("FLIGHT_AUTO_COMPLETE_URL"), headers=HEADERS, params={"query": city})
    data = resp.json()
    airports_data = data.get("data", [])
    if not airports_data:
        # No airports found for city
        return None, []

    airport_id = None
    airports = []

    # Extract airport info, pick first airport as main airport_id
    for airport in airports_data:
        if airport.get("type") == "AIRPORT":
            if not airport_id:
                airport_id = airport.get("code")
            airports.append({
                "airport_name": airport.get("name"),
                "airport_code": airport.get("code"),
                "city_name": airport.get("cityName"),
                "country_name": airport.get("countryName"),
                "distance_to_city": airport.get("distanceToCity", {}).get("value")
            })

    result = (airport_id, airports)

    # Cache the airport info in Redis
    await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


async def get_flight_details_price(token: str):
    """
    Get flight price details for a specific token.
    Cache results in Redis.
    """
    cache_key = f"flight_price:{token}"
    cached = await get_redis_client().get(cache_key)
    if cached:
        # Return cached price info if available
        return json.loads(cached)

    # Limit concurrent requests to avoid rate limiting
    async with semaphore:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(os.getenv("FLIGHT_DETAILS_URL"), headers=HEADERS, params={"token": token})
            if resp.status_code != 200:
                # If API fails, return None price and currency
                return {"price": None, "currency": None}
            data = resp.json()

            # Extract traveller price info from response
            price_info_list= data.get("data", {}).get("travellerPrices", [])
            price_info = price_info_list[0]  # assume first traveller price

            result = {
                "price": price_info.get("travellerPriceBreakdown", {}).get("totalRounded", {}).get("units"),
                "currency": price_info.get("travellerPriceBreakdown", {}).get("totalRounded", {}).get("currencyCode"),
            }

            # Cache price info in Redis
            await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(result))
            return result


def parse_segment(segment: Dict[str, Any], token: str, price_bhd: float,
                  base_currency: str, base_currency_date: str, travellers_count: int) -> Dict[str, Any]:
    """
    Parse a flight segment dictionary and extract detailed flight info,
    including legs, times, airports, carrier, and price info converted to BHD.
    """
    legs_info = []

    # Loop through each leg of the segment to extract flight details
    for leg in segment.get("legs", []):
        flight_number= str(
            str(leg.get("flightInfo", {}).get("carrierInfo", {}).get("operatingCarrier")) +
            str(leg.get("flightInfo", {}).get("flightNumber"))
        )

        legs_info.append({
            "departure_time": leg.get("departureTime"),
            "arrival_time": leg.get("arrivalTime"),
            "departure_airport": leg.get("departureAirport", {}).get("name"),
            "arrival_airport": leg.get("arrivalAirport", {}).get("name"),
            "departure_city": leg.get("departureAirport", {}).get("cityName"),
            "arrival_city": leg.get("arrivalAirport", {}).get("cityName"),
            "departure_country": leg.get("departureAirport", {}).get("countryName"),
            "arrival_country": leg.get("arrivalAirport", {}).get("countryName"),
            "cabin_class": leg.get("cabinClass"),
            "flight_number": flight_number,
            "arrivalTerminal": leg.get("arrivalTerminal"),
            "carrier": leg.get("carriersData", [{}])[0].get("name") if leg.get("carriersData") else None,
            "carrier_logo": leg.get("carriersData", [{}])[0].get("logo") if leg.get("carriersData") else None,
        })

    # Build and return the parsed segment info dictionary
    return {
        "token": token,
        "travellers_count": travellers_count,
        "price": price_bhd,
        "currency": "BHD",
        "base_currency": base_currency,
        "base_currency_date": base_currency_date,
        "departure_time": segment.get("departureTime"),
        "arrival_time": segment.get("arrivalTime"),
        "departure_city": segment.get("departureAirport", {}).get("cityName"),
        "departure_country": segment.get("departureAirport", {}).get("countryName"),
        "departure_airport": segment.get("departureAirport", {}).get("name"),
        "arrival_city": segment.get("arrivalAirport", {}).get("cityName"),
        "arrival_country": segment.get("arrivalAirport", {}).get("countryName"),
        "arrival_airport": segment.get("arrivalAirport", {}).get("name"),
        "duration_seconds": segment.get("totalTime"),
        "duration_hours": round(segment.get("totalTime", 0) / 3600, 2),
        "legs": legs_info
    }


async def get_flights(city_name: str, arrival_date: str, departure_date: str, departure_city_name: str):
    """
    Main function to fetch flight offers for a round trip:
    - Gets airport codes for departure and arrival cities,
    - Queries flight offers,
    - Fetches prices for each offer,
    - Converts prices to BHD,
    - Parses and separates outbound and return flights,
    - Caches results in Redis.
    """
    cache_key = f"flights:{city_name}:{arrival_date}:{departure_date}:{departure_city_name}"
    cached = await get_redis_client().get(cache_key)
    if cached:
        # Return cached flight offers if available
        return json.loads(cached)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Get arrival and departure airport info including codes and airport list
        arrival_id, arrival_airports = await get_airport_info(client, city_name)
        departure_id, departure_airports = await get_airport_info(client, departure_city_name)

        if not arrival_id or not departure_id:
            # If airports not found, raise 404 error
            raise HTTPException(status_code=404, detail="Could not find arrival or departure airport")

        # Prepare query parameters for flight search API
        querystring = {
            "departId": departure_id,
            "arrivalId": arrival_id,
            "departDate": arrival_date,
            "returnDate": departure_date
        }

        # Get flight offers, with caching and timeout handled by cached_get
        data = await cached_get(os.getenv("FLIGHT_ROUNDTRIP_URL"), params=querystring, headers=HEADERS, ttl=7200)

        # Limit flight offers to first 10 results to avoid large data
        flight_offers = data.get("data", {}).get("flightOffers", [])[:10]

        # Get exchange rate data once to convert prices to BHD
        exchange_data = await ExchangeRateService.get_rates()
        base_currency_code = exchange_data.get("base_currency", "BHD")
        base_currency_date = exchange_data.get("base_currency_date", "")

        # Collect tokens for each flight offer
        tokens = [offer.get("token") for offer in flight_offers]

        # Get prices for all tokens in parallel (with concurrency/semaphore)
        prices_data = await asyncio.gather(*[get_flight_details_price(t) for t in tokens])

        # Prepare lists to hold parsed outbound and return flights
        outbound_flights, return_flights = [], []

        # Iterate offers and their corresponding prices
        for i, offer in enumerate(flight_offers):
            token = tokens[i]
            price = prices_data[i]["price"]
            currency = prices_data[i]["currency"]
            travellers_count = len(offer.get("travellers", [])) or 1  # default to 1 if none

            price_in_bhd = None
            if price is not None and currency:
                # Convert price to BHD
                price_in_bhd = await ExchangeRateService.convert_to_bhd(price, currency)

            # Parse each segment (leg) of the flight offer
            for seg in offer.get("segments", []):
                parsed = parse_segment(seg, token, price_in_bhd,
                                       base_currency_code, base_currency_date, travellers_count)

                # Separate outbound vs return flights based on departure airport code
                if seg.get("departureAirport", {}).get("code") == departure_id:
                    outbound_flights.append(parsed)
                elif seg.get("departureAirport", {}).get("code") == arrival_id:
                    return_flights.append(parsed)

        # Prepare final result object including airport info and flight lists
        result = {
            "departure_airport_info": departure_airports,
            "arrival_airport_info": arrival_airports,
            "outbound": outbound_flights,
            "return": return_flights
        }

        # Cache the flight results in Redis for CACHE_TTL duration
        await get_redis_client().setex(cache_key, CACHE_TTL, json.dumps(result))
        return result


flightIn=flight_pydanticIn

async def post_flight_service(flight_info: flightIn, current_user: User):
    """
    Create a new flight record in the database linked to the current user.
    """
    flight_obj = await Flight.create(
        departure_airport_info=flight_info.departure_airport_info,
        arrival_airport_info=flight_info.arrival_airport_info,
        outbound_price=flight_info.outbound_price,
        outbound_currency=flight_info.outbound_currency,
        outbound_duration_hours=flight_info.outbound_duration_hours,
        outbound_departure_time=flight_info.outbound_departure_time,
        outbound_arrival_time=flight_info.outbound_arrival_time,
        outbound_cabin_class=flight_info.outbound_cabin_class,
        outbound_flight_number=flight_info.outbound_flight_number,
        outbound_carrier=flight_info.outbound_carrier,
        outbound_legs=flight_info.outbound_legs,
        return_price=flight_info.return_price,
        return_currency=flight_info.return_currency,
        return_duration_hours=flight_info.return_duration_hours,
        return_departure_time=flight_info.return_departure_time,
        return_arrival_time=flight_info.return_arrival_time,
        return_cabin_class=flight_info.return_cabin_class,
        return_flight_number=flight_info.return_flight_number,
        return_carrier=flight_info.return_carrier,
        return_legs=flight_info.return_legs,
        related_user_id=current_user.id
    )

    return {
        "status": "Ok",
        "data": await flight_pydantic.from_tortoise_orm(flight_obj)
    }


async def get_all_flights_service(current_user: User):
    """
    Service to get all flights saved by the current user from the database.
    Raises HTTP 404 if no flights found.
    """
    get_all_flights_res = await flight_pydantic.from_queryset(
        Flight.filter(related_user=current_user.id)  
    )
    if not get_all_flights_res:
        raise HTTPException(status_code=404, detail="No flights found for this user")
    return {"status": "Ok", "data": get_all_flights_res}
