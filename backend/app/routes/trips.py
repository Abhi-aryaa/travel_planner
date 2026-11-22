"""REST endpoints for trips, destinations, activities and travel documents."""
import base64

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from .. import schemas
from ..config import settings
from ..db import trips_collection
from ..services import trips as svc

router = APIRouter(prefix="/api/trips", tags=["trips"])

ALLOWED_DOC_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp", "text/plain"}


@router.get("")
async def list_trips():
    return await svc.list_trips()


@router.post("", status_code=201)
async def create_trip(body: schemas.TripCreate):
    return await svc.create_trip(body.model_dump())


@router.get("/{trip_id}")
async def get_trip(trip_id: str):
    return await svc.get_trip(trip_id)


@router.patch("/{trip_id}")
async def update_trip(trip_id: str, body: schemas.TripUpdate):
    return await svc.update_trip(trip_id, body.model_dump())


@router.delete("/{trip_id}", status_code=204)
async def delete_trip(trip_id: str):
    await svc.delete_trip(trip_id)


@router.get("/{trip_id}/budget")
async def get_budget(trip_id: str):
    return (await svc.get_trip(trip_id))["budget_summary"]


# ---- Destinations -------------------------------------------------------
@router.post("/{trip_id}/destinations", status_code=201)
async def add_destination(trip_id: str, body: schemas.DestinationCreate):
    return await svc.push_item(trip_id, "destinations", body.model_dump())


@router.patch("/{trip_id}/destinations/{dest_id}")
async def update_destination(trip_id: str, dest_id: str, body: schemas.DestinationUpdate):
    return await svc.update_item(trip_id, "destinations", dest_id, body.model_dump())


@router.delete("/{trip_id}/destinations/{dest_id}")
async def delete_destination(trip_id: str, dest_id: str):
    return await svc.delete_item(trip_id, "destinations", dest_id)


# ---- Activities ---------------------------------------------------------
@router.post("/{trip_id}/activities", status_code=201)
async def add_activity(trip_id: str, body: schemas.ActivityCreate):
    return await svc.push_item(trip_id, "activities", body.model_dump())


@router.patch("/{trip_id}/activities/{activity_id}")
async def update_activity(trip_id: str, activity_id: str, body: schemas.ActivityUpdate):
    return await svc.update_item(trip_id, "activities", activity_id, body.model_dump(exclude_unset=True))


@router.delete("/{trip_id}/activities/{activity_id}")
async def delete_activity(trip_id: str, activity_id: str):
    return await svc.delete_item(trip_id, "activities", activity_id)


# ---- Travel documents (tickets, passports, bookings) ---------------------
@router.post("/{trip_id}/documents", status_code=201)
async def upload_document(trip_id: str, file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(415, "Only PDF, PNG, JPEG, WEBP or TXT files are allowed")
    data = await file.read()
    if len(data) > settings.MAX_DOCUMENT_BYTES:
        raise HTTPException(413, "File exceeds 2 MB limit")
    item = {"name": file.filename, "content_type": file.content_type, "size": len(data),
            "data": base64.b64encode(data).decode()}
    return await svc.push_item(trip_id, "documents", item)


@router.get("/{trip_id}/documents/{doc_id}")
async def download_document(trip_id: str, doc_id: str):
    trip = await svc.get_trip_raw(trip_id)
    doc = next((d for d in trip.get("documents", []) if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(404, "Document not found")
    return Response(base64.b64decode(doc["data"]), media_type=doc["content_type"],
                    headers={"Content-Disposition": f'inline; filename="{doc["name"]}"'})


@router.delete("/{trip_id}/documents/{doc_id}")
async def delete_document(trip_id: str, doc_id: str):
    return await svc.delete_item(trip_id, "documents", doc_id)
