"""Historical vendor data (Binance public dumps): download + inventory."""
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/history", tags=["History"])


def _local_only(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Only available from the local machine.")


@router.get("/status")
def history_status():
    from apps.api.services import history_runner
    return history_runner.status()


@router.post("/download")
def history_download(request: Request, months: int = 12):
    _local_only(request)
    from apps.api.services import history_runner
    return history_runner.start(months=max(1, min(months, 36)))


@router.post("/download_hourly")
def history_download_hourly(request: Request, days: int = 1460):
    _local_only(request)
    from apps.api.services import history_runner
    return history_runner.start_hourly(days=max(60, min(days, 2200)))
