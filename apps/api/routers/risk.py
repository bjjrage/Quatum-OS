"""Deterministic Risk Engine, EventClusters, and Kill Switches endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api", tags=["Risk"])


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
            "current_gross_usd": 0.0,
            "current_net_usd": 0.0,
            "stress_loss_usd": 0.0,
            "status": "ARMED",
            "diversification_warning": "Same strategy across multiple accounts != diversification. Different venue != diversification.",
        })
    return clusters
