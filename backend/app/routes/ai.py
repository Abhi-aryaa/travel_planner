"""Chatbot endpoints: trip assistant and AI itinerary generator."""
from datetime import date

from fastapi import APIRouter

from .. import schemas
from ..services import ai, trips as trip_svc
from ..services.places import search_places

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/trips/{trip_id}/chat")
async def chat(trip_id: str, body: schemas.ChatRequest):
    trip = await trip_svc.get_trip_raw(trip_id)
    return await ai.chat(trip, body.message)


@router.post("/generate", status_code=201)
async def generate(body: schemas.GenerateRequest):
    result = await ai.generate_itinerary(body.prompt)
    destinations = []
    try:  # pin the main destination on the map
        hits = await search_places(result["destination"])
        if hits:
            h = hits[0]
            destinations.append({**schemas.DestinationCreate(
                name=h["name"], place_id=h["place_id"], address=h["address"], lat=h["lat"], lng=h["lng"],
                rating=h["rating"], notes="Added by AI itinerary generator").model_dump(),
                "id": trip_svc.new_id()})
    except Exception:
        pass
    activities = []
    for a in result["activities"]:
        a = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in a.items()}
        a["id"] = trip_svc.new_id()
        a["destination_id"] = destinations[0]["id"] if destinations else None
        activities.append(a)
    trip = await trip_svc.create_trip(result["trip"], activities=activities, destinations=destinations)
    trip["generated_by"] = result["source"]
    return trip
