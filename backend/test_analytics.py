import requests
import uuid
import json

API_BASE = "http://localhost:8000/api/v1/analytics"

def test_track_event():
    payload = {
        "event_name": "dashboard_viewed",
        "session_id": str(uuid.uuid4()),
        "anon_id": "test_hash_123",
        "page": "/dashboard",
        "properties": {"test": True}
    }
    print("Testing POST /event...")
    try:
        resp = requests.post(f"{API_BASE}/event", json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_track_event()
