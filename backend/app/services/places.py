"""Place search + geolocation. Google Places API (New) with OpenStreetMap fallback."""
import httpx
from fastapi import HTTPException

from ..config import settings

GOOGLE_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_FIELDS = ("places.id,places.displayName,places.formattedAddress,places.location,"
                 "places.rating,places.userRatingCount,places.types,places.googleMapsUri")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


async def _google_search(query: str) -> list:
    headers = {"X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY, "X-Goog-FieldMask": GOOGLE_FIELDS}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(GOOGLE_URL, json={"textQuery": query, "pageSize": 6}, headers=headers)
    if r.status_code != 200:
        raise HTTPException(502, f"Google Places error: {r.json().get('error', {}).get('message', r.text)}")
    return [
        {
            "place_id": p.get("id"),
            "name": p.get("displayName", {}).get("text", ""),
            "address": p.get("formattedAddress", ""),
            "lat": p["location"]["latitude"],
            "lng": p["location"]["longitude"],
            "rating": p.get("rating"),
            "user_ratings_total": p.get("userRatingCount"),
            "types": p.get("types", [])[:3],
            "maps_url": p.get("googleMapsUri"),
        }
        for p in r.json().get("places", []) if p.get("location")
    ]


async def _osm_search(query: str) -> list:
    params = {"q": query, "format": "json", "limit": 6, "addressdetails": 0}
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "travel-planner-app/1.0"}) as client:
        r = await client.get(NOMINATIM_URL, params=params)
    if r.status_code != 200:
        raise HTTPException(502, "Geocoding service unavailable")
    return [
        {
            "place_id": f"osm:{p['osm_type']}:{p['osm_id']}",
            "name": p.get("name") or p["display_name"].split(",")[0],
            "address": p["display_name"],
            "lat": float(p["lat"]),
            "lng": float(p["lon"]),
            "rating": None,
            "user_ratings_total": None,
            "types": [p.get("type", "")],
            "maps_url": None,
        }
        for p in r.json()
    ]


async def search_places(query: str) -> list:
    query = query.strip()
    if len(query) < 2:
        raise HTTPException(422, "Query must be at least 2 characters")
    if settings.GOOGLE_MAPS_API_KEY:
        try:
            return await _google_search(query)
        except HTTPException:
            pass  # degrade gracefully to OSM so the app keeps working
    return await _osm_search(query)
