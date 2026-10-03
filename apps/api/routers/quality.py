"""Data Quality & Acceptance metrics endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/data-quality", tags=["Data Quality"])


@router.get("")
def get_data_quality():
    svc = QuantOSDataService.get_instance()
    return svc.get_data_quality()


@router.get("/incidents")
def get_data_quality_incidents():
    svc = QuantOSDataService.get_instance()
    dq = svc.get_data_quality()
    if dq.get("status") == "NOT_AVAILABLE":
        return {"status": "NOT_AVAILABLE", "incidents": []}

    ts = dq.get("timestamp_integrity", {})
    incidents = []
    if ts.get("is_host_clock_skew_detected"):
        incidents.append({
            "type": "HOST_CLOCK_SKEW",
            "severity": "WARNING",
            "estimated_offset_ms": ts.get("estimated_clock_offset_ms"),
            "description": "Local operating system clock is lagging exchange timestamp. Transit latencies mathematically corrected.",
        })

    violations = ts.get("true_causal_violations", 0)
    if violations > 0:
        incidents.append({
            "type": "CAUSAL_VIOLATION",
            "severity": "CRITICAL",
            "count": violations,
            "description": "Events received with timestamps predating causality horizon.",
        })

    return {
        "status": "AVAILABLE",
        "incidents_count": len(incidents),
        "incidents": incidents,
    }
