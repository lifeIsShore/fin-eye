"""
app/schemas/alert_models.py
Pydantic schemas for alert CRUD and responses.
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


VALID_ALERT_TYPES = {"price_above", "price_below", "gas_above", "gas_below"}
VALID_CHANNELS = {"in_app", "email"}


class AlertCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    alert_type: str = Field(..., description="price_above | price_below | gas_above | gas_below")
    threshold: float = Field(..., description="Numeric threshold that triggers the alert")
    delivery_channel: str = Field(default="in_app", description="in_app | email")

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("alert_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        if v not in VALID_ALERT_TYPES:
            raise ValueError(f"alert_type must be one of {sorted(VALID_ALERT_TYPES)}")
        return v

    @field_validator("delivery_channel")
    @classmethod
    def valid_channel(cls, v: str) -> str:
        if v not in VALID_CHANNELS:
            raise ValueError(f"delivery_channel must be one of {sorted(VALID_CHANNELS)}")
        return v


class AlertResponse(BaseModel):
    id: int
    symbol: str
    alert_type: str
    threshold: float
    delivery_channel: str
    is_active: bool
    triggered_at: Optional[datetime]
    triggered_value: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int


class TriggeredAlertResponse(BaseModel):
    """Returned when polling for newly-fired alerts."""
    id: int
    symbol: str
    alert_type: str
    threshold: float
    triggered_value: float
    triggered_at: datetime
    message: str

    model_config = {"from_attributes": True}


class AlertHistoryResponse(BaseModel):
    """One entry in the alert history log (triggered + dismissed)."""
    id: int
    symbol: str
    alert_type: str
    threshold: float
    delivery_channel: str
    triggered_value: float
    triggered_at: datetime
    is_active: bool          # False = dismissed/acknowledged, True = still showing
    created_at: datetime
    message: str

    model_config = {"from_attributes": True}


class AlertHistoryListResponse(BaseModel):
    history: List[AlertHistoryResponse]
    total: int
