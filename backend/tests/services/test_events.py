import pytest
from app.services.event_service import EventService

@pytest.fixture
def event_service():
    return EventService()

@pytest.mark.asyncio
async def test_get_upcoming_events(event_service):
    events = await event_service.get_upcoming_events()
    assert len(events) > 0
    assert hasattr(events[0], "title")
    assert hasattr(events[0], "impact")

@pytest.mark.asyncio
async def test_get_upcoming_events_with_country_filter(event_service):
    events = await event_service.get_upcoming_events(country="US")
    for event in events:
        assert event.country == "US"
        
@pytest.mark.asyncio
async def test_get_upcoming_events_with_impact_filter(event_service):
    events = await event_service.get_upcoming_events(impact="High")
    for event in events:
        assert event.impact == "High"
