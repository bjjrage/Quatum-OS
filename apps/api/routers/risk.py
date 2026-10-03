"""Deterministic Risk Engine, EventClusters, and Kill Switches endpoints."""
from typing import Any, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.auth import require_operator_auth
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api", tags=["Risk"])


class KillSwitchActionRequest(BaseModel):
    scope: str = Field(default="GLOBAL", description="Scope: GLOBAL, VENUE, ACCOUNT, STRATEGY, SYMBOL")
    reason: str = Field(..., description="Operational reason for triggering/resetting kill switch")
    target: str = Field(default="", description="Specific target identifier when scope is not GLOBAL")


@router.get("/risk/status")
def get_risk_status():
    svc = QuantOSDataService.get_instance()
    return svc.get_risk_status()


@router.get("/risk/decisions")
def get_risk_decisions():
    svc = QuantOSDataService.get_instance()
    return svc.risk_decisions


@router.get("/risk/kill-switches")
def get_kill_switches():
    svc = QuantOSDataService.get_instance()
    r = svc.get_risk_status()
    return r.get("kill_switches", {})


@router.post("/risk/kill-switch/activate")
def activate_kill_switch(
    payload: KillSwitchActionRequest,
    operator: str = Depends(require_operator_auth),
) -> Dict[str, Any]:
    """Privileged operator mutation: activate scoped kill switch with persistence."""
    svc = QuantOSDataService.get_instance()
    try:
        return svc.activate_kill_switch(
            scope=payload.scope,
            actor=f"OPERATOR:{operator[:16]}",
            reason=payload.reason,
            target=payload.target,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/risk/kill-switch/reset")
def reset_kill_switch(
    payload: KillSwitchActionRequest,
    operator: str = Depends(require_operator_auth),
) -> Dict[str, Any]:
    """Privileged operator mutation: reset scoped kill switch with persistence."""
    svc = QuantOSDataService.get_instance()
    try:
        return svc.reset_kill_switch(
            scope=payload.scope,
            actor=f"OPERATOR:{operator[:16]}",
            reason=payload.reason,
            target=payload.target,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/event-clusters")
def get_event_clusters():
    svc = QuantOSDataService.get_instance()
    clusters = []
    for ec in svc.event_clusters.values():
        clusters.append({
            "cluster_id": ec.cluster_id,
            "description": ec.description,
            "max_gross_exposure_usd": ec.max_gross_exposure_usd,
            "max_net_exposure_usd": ec.max_net_exposure_usd,
            "stress_loss_limit_usd": ec.stress_loss_limit_usd,
            "stress_factor": ec.stress_factor,
            "member_weights": ec.member_weights,
            "current_gross_usd": None,
            "current_net_usd": None,
            "stress_loss_usd": None,
            "status": "ARMED",
            "exposure_state": "NOT_TRACKED",
            "data_source": "MOCK" if svc.mock_mode else "CONFIG",
            "diversification_warning": "Same strategy across multiple accounts != diversification. Different venue != diversification.",
        })
    return clusters
