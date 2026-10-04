"""Data Recorder & Continuity status endpoints."""
from fastapi import APIRouter, HTTPException, Request
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


def _local_only(request: Request) -> None:
    """Recorder control is a local-workstation action: only loopback callers (the cockpit) may use it."""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Recorder control is only available from the local machine.")


@router.post("/start")
def start_recorder(request: Request, new_run: bool = False):
    _local_only(request)
    from apps.api.services import recorder_control
    return recorder_control.start(new_run=new_run)


@router.post("/stop")
def stop_recorder(request: Request):
    _local_only(request)
    from apps.api.services import recorder_control
    return recorder_control.stop()
