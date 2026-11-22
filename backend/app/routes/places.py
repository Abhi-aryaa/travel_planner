from fastapi import APIRouter, Query

from ..services.places import search_places

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("/search")
async def search(q: str = Query(..., min_length=2, max_length=200)):
    return await search_places(q)
