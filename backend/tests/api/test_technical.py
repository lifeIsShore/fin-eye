import pytest

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_latest_technical_consensus(client: AsyncClient, test_app, test_db, monkeypatch):
    # Patch consensus builder to avoid filesystem/model loading in this API test
    from app.services.technical_consensus import TechnicalConsensus, TimeframeSignal
    from app.services.technical_models import Timeframe

    def fake_build_consensus_for_symbol(**kwargs):
        return TechnicalConsensus(
            consensus=0.5,
            technical_confidence_score=75.0,
            summary="Mostly bullish",
            signals=[
                TimeframeSignal(
                    timeframe=Timeframe.ONE_DAY,
                    direction=1,
                    confidence=0.8,
                    sharpe_weight=1.2,
                )
            ],
        )

    import app.api.v1.endpoints.technical as technical_ep

    monkeypatch.setattr(technical_ep, "build_consensus_for_symbol", fake_build_consensus_for_symbol)

    res = await client.get("/api/v1/technical/AAPL/latest")
    assert res.status_code == 200
    payload = res.json()
    assert payload["symbol"] == "AAPL"
    assert payload["technical_confidence_score"] == 75.0
    assert payload["summary"] == "Mostly bullish"
    assert isinstance(payload["signals"], list)

