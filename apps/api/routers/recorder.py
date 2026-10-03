"""Data Recorder & Continuity status endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/recorder", tags=["Recorder"])


@router.get("/status")
def get_recorder_status():
    svc = QuantOSDataService.get_instance()
    return svc.get_recorder_status()


@router.get("/continuity")
def get_recorder_continuity():
    svc = QuantOSDataService.get_instance()
    rec = svc.get_recorder_status()
    return {
        "status": "AVAILABLE",
        "run_id": rec.get("run_id"),
        "continuity_state": rec.get("continuity_state", "UNVERIFIED"),
        "continuity_reason": rec.get("continuity_reason", "NOT_AVAILABLE"),
        "config_fingerprint": rec.get("config_fingerprint"),
        "heartbeat_at_utc": rec.get("heartbeat_at_utc"),
        "is_process_alive": rec.get("is_process_alive", False),
    }
