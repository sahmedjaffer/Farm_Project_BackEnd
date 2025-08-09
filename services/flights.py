import httpx, asyncio, json, os
from fastapi import HTTPException
from typing import Dict, Any
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

TIMEOUT = 30.0

# API URLs


# Cache & Concurrency settings
CACHE_TTL = 86400  # 24 hours
semaphore = asyncio.Semaphore(3)


async def get_airport_info(client: httpx.AsyncClient, city: str):
    cache_key = f"airport_info:{city}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    resp = await client.get(os.getenv("FLIGHT_AUTO_COMPLETE_URL"), headers=HEADERS, params={"query": city})
    data = resp.json()
    airports_data = data.get("data", [])
    if not airports_data:
        return None, []

    airport_id = None
    airports = []
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
    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


async def get_flight_details_price(token: str):
    cache_key = f"flight_price:{token}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    async with semaphore:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(os.getenv("FLIGHT_DETAILS_URL"), headers=HEADERS, params={"token": token})
            if resp.status_code != 200:
                return {"price": None, "currency": None}
            data = resp.json()
            price_info_list= data.get("data", {}).get("travellerPrices", [])
            price_info = price_info_list[0]
            result = {
                "price": price_info.get("travellerPriceBreakdown", {}).get("totalRounded", {}).get("units"),
                "currency": price_info.get("travellerPriceBreakdown", {}).get("totalRounded", {}).get("currencyCode"),
            }
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
            return result


def parse_segment(segment: Dict[str, Any], token: str, price_bhd: float,
                  base_currency: str, base_currency_date: str, travellers_count: int) -> Dict[str, Any]:
    legs_info = []
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
            "arrivalTerminal":leg.get("arrivalTerminal"),
            "carrier": leg.get("carriersData", [{}])[0].get("name") if leg.get("carriersData") else None,
            "carrier_logo": leg.get("carriersData", [{}])[0].get("logo") if leg.get("carriersData") else None,
        })

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
    cache_key = f"flights:{city_name}:{arrival_date}:{departure_date}:{departure_city_name}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        arrival_id, arrival_airports = await get_airport_info(client, city_name)
        departure_id, departure_airports = await get_airport_info(client, departure_city_name)

        if not arrival_id or not departure_id:
            raise HTTPException(status_code=404, detail="Could not find arrival or departure airport")

        querystring = {
            "departId": departure_id,
            "arrivalId": arrival_id,
            "departDate": arrival_date,
            "returnDate": departure_date
        }
        data = await cached_get(os.getenv("FLIGHT_ROUNDTRIP_URL"), params=querystring, headers=HEADERS, ttl=7200)


        flight_offers = data.get("data", {}).get("flightOffers", [])[:10]  # limit results

        # Get exchange rate data once
        exchange_data = await ExchangeRateService.get_rates()
        base_currency_code = exchange_data.get("base_currency", "BHD")
        base_currency_date = exchange_data.get("base_currency_date", "")

        # Get prices in parallel (with cache + semaphore)
        tokens = [offer.get("token") for offer in flight_offers]
        prices_data = await asyncio.gather(*[get_flight_details_price(t) for t in tokens])

        outbound_flights, return_flights = [], []

        for i, offer in enumerate(flight_offers):
            token = tokens[i]
            price = prices_data[i]["price"]
            currency = prices_data[i]["currency"]
            travellers_count = len(offer.get("travellers", [])) or 1

            price_in_bhd = None
            if price is not None and currency:
                price_in_bhd = await ExchangeRateService.convert_to_bhd(price, currency)

            for seg in offer.get("segments", []):
                parsed = parse_segment(seg, token, price_in_bhd,
                                       base_currency_code, base_currency_date, travellers_count,)

                if seg.get("departureAirport", {}).get("code") == departure_id:
                    outbound_flights.append(parsed)
                elif seg.get("departureAirport", {}).get("code") == arrival_id:
                    return_flights.append(parsed)

        result = {
            "departure_airport_info": departure_airports,
            "arrival_airport_info": arrival_airports,
            "outbound": outbound_flights,
            "return": return_flights
        }
        await redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
        return result
