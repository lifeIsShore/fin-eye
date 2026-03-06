import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from datetime import date

# Import all models so Base.metadata is fully populated before
# conftest.py creates the SQLite in-memory schema.
import app.models  # noqa: F401 — side-effect import
from app.models.macro import MacroIndicator

# Mock data for our database
mock_macro_data = [
    MacroIndicator(indicator_name="fed_funds_rate", value=5.25, date=date(2023, 10, 1)),
    MacroIndicator(indicator_name="unemployment_rate", value=3.8, date=date(2023, 10, 1)),
    MacroIndicator(indicator_name="yield_spread_10y_2y", value=-0.5, date=date(2023, 10, 1)),
    MacroIndicator(indicator_name="cpi_yoy", value=3.2, date=date(2023, 10, 1)),
    MacroIndicator(indicator_name="vix", value=15.5, date=date(2023, 10, 1)),
]

@pytest.mark.asyncio
async def test_get_latest_macro_dashboard(client: AsyncClient, test_app, test_db):
    # Setup test DB - test_db is injected via conftest.py and also wired into the client
    test_db.add_all(mock_macro_data)
    test_db.commit()

    response = await client.get("/api/v1/macro/latest")
    assert response.status_code == 200

    payload = response.json()
    data = payload.get("data")
    assert data is not None
    
    # Check if all indicators are present
    assert "fed_funds_rate" in data
    assert "unemployment_rate" in data
    assert "yield_spread_10y_2y" in data
    assert "cpi_yoy" in data
    assert "vix" in data
    
    # Verify values and interpretations
    assert data["fed_funds_rate"]["value"] == 5.25
    assert "restrictive" in data["fed_funds_rate"]["interpretation"].lower()
    
    assert data["yield_spread_10y_2y"]["value"] == -0.5
    assert "inverted" in data["yield_spread_10y_2y"]["interpretation"].lower()

    # Macro score should be present and within 0–100 with a label
    macro_score = payload.get("macro_score")
    assert macro_score is not None
    assert 0 <= macro_score["score"] <= 100
    assert macro_score["label"] in {"Supportive", "Neutral", "Stressed"}

@pytest.mark.asyncio
@patch('app.api.v1.endpoints.macro.refresh_all_macro_indicators')
async def test_refresh_macro_data(mock_refresh, client: AsyncClient):
    mock_refresh.return_value = None
    
    response = await client.post("/api/v1/macro/refresh")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    mock_refresh.assert_called_once()
