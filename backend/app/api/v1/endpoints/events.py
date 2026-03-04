from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.schemas.event_models import EventResponse
from app.services.event_service import EventService

router = APIRouter()
event_service = EventService()

@router.get("/upcoming", response_model=EventResponse)
async def get_upcoming_events(
    country: Optional[str] = Query(None, description="Filter events by country code (e.g. US, EU)"),
    impact: Optional[str] = Query(None, description="Filter events by impact (Low, Medium, High)")
):
    """
    Retrieve a list of upcoming macroeconomic and political events.
    """
    events = await event_service.get_upcoming_events(country=country, impact=impact)
    return EventResponse(events=events)
