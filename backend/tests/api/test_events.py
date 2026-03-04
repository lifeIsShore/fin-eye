import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_upcoming_events_endpoint():
    response = client.get("/api/v1/events/upcoming")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert len(data["events"]) > 0
    
def test_get_upcoming_events_endpoint_filtered():
    response = client.get("/api/v1/events/upcoming?country=US&impact=High")
    assert response.status_code == 200
    data = response.json()
    for event in data["events"]:
        assert event["country"] == "US"
        assert event["impact"] == "High"
