"""Trip business logic: persistence, timeline ordering and serialization."""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException

from ..db import trips_collection
from .budget import compute_budget


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _oid(trip_id: str) -> ObjectId:
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(404, "Trip not found")
    return ObjectId(trip_id)


def _jsonable(value):
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    return value


def build_timeline(trip: dict) -> list:
    """Group activities by day, sorted chronologically (server-side ordering)."""
    dest_names = {d["id"]: d["name"] for d in trip.get("destinations", [])}
    days: dict = {}
    for a in sorted(trip.get("activities", []), key=lambda a: (str(a["date"]), a.get("time", ""))):
        item = dict(a, destination_name=dest_names.get(a.get("destination_id")))
        days.setdefault(str(a["date"]), []).append(item)
    start = trip.get("start_date")
    out = []
    for i, (d, items) in enumerate(days.items()):
        try:
            day_no = (date.fromisoformat(d) - date.fromisoformat(str(start))).days + 1
        except ValueError:
            day_no = i + 1
        out.append({"date": d, "day_number": day_no, "activities": items})
    return out


def serialize(trip: dict) -> dict:
    trip = _jsonable(trip)
    trip["id"] = trip.pop("_id")
    docs = trip.get("documents", [])
    # Never send file payloads in the trip listing; they are fetched separately.
    trip["documents"] = [{k: v for k, v in d.items() if k != "data"} for d in docs]
    trip["timeline"] = build_timeline(trip)
    trip["budget_summary"] = compute_budget(trip)
    return trip


async def list_trips() -> list:
    cursor = trips_collection().find({}, {"documents.data": 0}).sort("created_at", -1)
    return [
        {"id": str(t["_id"]), "name": t["name"], "start_date": str(t["start_date"]),
         "end_date": str(t["end_date"]), "budget_summary": compute_budget(t)}
        async for t in cursor
    ]


async def get_trip_raw(trip_id: str) -> dict:
    trip = await trips_collection().find_one({"_id": _oid(trip_id)})
    if not trip:
        raise HTTPException(404, "Trip not found")
    return trip


async def get_trip(trip_id: str) -> dict:
    return serialize(await get_trip_raw(trip_id))


async def create_trip(data: dict, activities: Optional[list] = None, destinations: Optional[list] = None) -> dict:
    doc = {
        **{k: (v.isoformat() if isinstance(v, date) else v) for k, v in data.items()},
        "destinations": destinations or [],
        "activities": activities or [],
        "documents": [],
        "created_at": datetime.now(timezone.utc),
    }
    res = await trips_collection().insert_one(doc)
    return await get_trip(str(res.inserted_id))


async def update_trip(trip_id: str, fields: dict) -> dict:
    fields = {k: v for k, v in fields.items() if v is not None}
    if fields:
        await trips_collection().update_one({"_id": _oid(trip_id)}, {"$set": fields})
    return await get_trip(trip_id)


async def delete_trip(trip_id: str) -> None:
    res = await trips_collection().delete_one({"_id": _oid(trip_id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "Trip not found")


def _check_in_range(trip: dict, d: str) -> None:
    if not (str(trip["start_date"]) <= d <= str(trip["end_date"])):
        raise HTTPException(422, f"Activity date {d} is outside the trip dates")


async def push_item(trip_id: str, array: str, item: dict) -> dict:
    trip = await get_trip_raw(trip_id)
    item = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in item.items()}
    if array == "activities":
        _check_in_range(trip, item["date"])
        if item.get("destination_id") and item["destination_id"] not in {d["id"] for d in trip["destinations"]}:
            raise HTTPException(422, "Unknown destination_id")
    item["id"] = new_id()
    await trips_collection().update_one({"_id": trip["_id"]}, {"$push": {array: item}})
    return await get_trip(trip_id)


async def update_item(trip_id: str, array: str, item_id: str, fields: dict) -> dict:
    trip = await get_trip_raw(trip_id)
    items = trip.get(array, [])
    target = next((i for i in items if i["id"] == item_id), None)
    if not target:
        raise HTTPException(404, "Item not found")
    for k, v in fields.items():
        if v is None and k != "actual_cost":
            continue
        target[k] = v.isoformat() if isinstance(v, date) else v
    if array == "activities":
        _check_in_range(trip, target["date"])
    await trips_collection().update_one({"_id": trip["_id"]}, {"$set": {array: items}})
    return await get_trip(trip_id)


async def delete_item(trip_id: str, array: str, item_id: str) -> dict:
    trip = await get_trip_raw(trip_id)
    update = {"$pull": {array: {"id": item_id}}}
    await trips_collection().update_one({"_id": trip["_id"]}, update)
    if array == "destinations":  # detach activities that referenced this destination
        acts = [dict(a, destination_id=None) if a.get("destination_id") == item_id else a
                for a in trip.get("activities", [])]
        await trips_collection().update_one({"_id": trip["_id"]}, {"$set": {"activities": acts}})
    return await get_trip(trip_id)
