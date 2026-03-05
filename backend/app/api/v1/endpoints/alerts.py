"""
app/api/v1/endpoints/alerts.py
REST endpoints for user-defined price / GAS alerts.

Routes (all auth-protected):
    POST   /alerts            — create a new alert
    GET    /alerts            — list all alerts for current user
    DELETE /alerts/{id}       — delete an alert
    GET    /alerts/triggered  — poll for fired-but-undismissed alerts
    POST   /alerts/{id}/ack   — dismiss a triggered alert
"""
import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.alert_models import (
    AlertCreate,
    AlertListResponse,
    AlertResponse,
    TriggeredAlertResponse,
)
from app.services.alert_service import (
    acknowledge_alert,
    build_trigger_message,
    create_alert,
    delete_alert,
    get_triggered_alerts,
    list_alerts,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new price or GAS alert",
)
async def create(
    body: AlertCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    alert = await create_alert(db, current_user, body)
    await db.commit()
    return alert


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List all alerts for the authenticated user",
)
async def list_all(
    active_only: bool = False,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    alerts = await list_alerts(db, current_user, active_only=active_only)
    return AlertListResponse(alerts=alerts, total=len(alerts))


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an alert",
)
async def remove(
    alert_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await delete_alert(db, alert_id, current_user)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    await db.commit()


@router.get(
    "/triggered",
    response_model=List[TriggeredAlertResponse],
    summary="Poll for fired-but-undismissed alerts",
)
async def triggered(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> List[TriggeredAlertResponse]:
    alerts = await get_triggered_alerts(db, current_user)
    return [
        TriggeredAlertResponse(
            id=a.id,
            symbol=a.symbol,
            alert_type=a.alert_type,
            threshold=a.threshold,
            triggered_value=a.triggered_value,
            triggered_at=a.triggered_at,
            message=build_trigger_message(a),
        )
        for a in alerts
    ]


@router.post(
    "/{alert_id}/ack",
    response_model=AlertResponse,
    summary="Dismiss (acknowledge) a triggered alert",
)
async def ack(
    alert_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    alert = await acknowledge_alert(db, alert_id, current_user)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    await db.commit()
    return alert
