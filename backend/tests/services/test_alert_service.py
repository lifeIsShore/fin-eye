"""
tests/services/test_alert_service.py
Unit tests for alert_service.py evaluation engine.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.alert import Alert
from app.services.alert_service import (
    build_trigger_message,
    evaluate_alerts_for_symbol,
)


def _make_db_alert(id, alert_type, threshold):
    a = Alert()
    a.id = id
    a.symbol = "AAPL"
    a.alert_type = alert_type
    a.threshold = threshold
    a.is_active = True
    a.triggered_at = None
    a.triggered_value = None
    a.delivery_channel = "in_app"
    a.created_at = datetime(2026, 3, 5)
    return a


class TestEvaluateAlerts:
    @pytest.mark.asyncio
    async def test_price_above_fires(self):
        alert = _make_db_alert(1, "price_above", 190.0)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[alert])))))
        db.flush = AsyncMock()

        fired = await evaluate_alerts_for_symbol(db, "AAPL", current_price=195.0)
        assert len(fired) == 1
        assert fired[0].triggered_value == 195.0
        assert fired[0].triggered_at is not None

    @pytest.mark.asyncio
    async def test_price_above_does_not_fire_below_threshold(self):
        alert = _make_db_alert(1, "price_above", 200.0)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[alert])))))
        db.flush = AsyncMock()

        fired = await evaluate_alerts_for_symbol(db, "AAPL", current_price=195.0)
        assert len(fired) == 0

    @pytest.mark.asyncio
    async def test_price_below_fires(self):
        alert = _make_db_alert(2, "price_below", 150.0)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[alert])))))
        db.flush = AsyncMock()

        fired = await evaluate_alerts_for_symbol(db, "AAPL", current_price=140.0)
        assert len(fired) == 1
        assert fired[0].triggered_value == 140.0

    @pytest.mark.asyncio
    async def test_gas_above_fires(self):
        alert = _make_db_alert(3, "gas_above", 70.0)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[alert])))))
        db.flush = AsyncMock()

        fired = await evaluate_alerts_for_symbol(db, "AAPL", current_price=200.0, current_gas=75.0)
        assert len(fired) == 1
        assert fired[0].triggered_value == 75.0

    @pytest.mark.asyncio
    async def test_gas_alert_skipped_when_gas_not_provided(self):
        alert = _make_db_alert(4, "gas_above", 70.0)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[alert])))))
        db.flush = AsyncMock()

        fired = await evaluate_alerts_for_symbol(db, "AAPL", current_price=200.0, current_gas=None)
        assert len(fired) == 0

    @pytest.mark.asyncio
    async def test_no_alerts_returns_empty(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
        db.flush = AsyncMock()

        fired = await evaluate_alerts_for_symbol(db, "AAPL", current_price=200.0)
        assert fired == []


class TestBuildTriggerMessage:
    def test_price_above_message(self):
        a = _make_db_alert(1, "price_above", 190.0)
        a.triggered_value = 195.5
        msg = build_trigger_message(a)
        assert "rose above" in msg
        assert "190.00" in msg
        assert "195.50" in msg
        assert "AAPL" in msg

    def test_price_below_message(self):
        a = _make_db_alert(2, "price_below", 150.0)
        a.triggered_value = 145.0
        msg = build_trigger_message(a)
        assert "fell below" in msg
        assert "price" in msg

    def test_gas_above_message(self):
        a = _make_db_alert(3, "gas_above", 70.0)
        a.triggered_value = 75.0
        msg = build_trigger_message(a)
        assert "GAS score" in msg
        assert "rose above" in msg
