"""Real-time SSE event stream endpoint for operational workstation."""
import asyncio
import json
import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/stream", tags=["Streaming"])


@router.get("/events")
async def stream_events():
    """Server-Sent Events stream emitting heartbeats, recorder status, and risk state."""
    async def event_generator():
        svc = QuantOSDataService.get_instance()
        while True:
            rec = svc.get_recorder_status()
            risk = svc.get_risk_status()
            payload = {
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "recorder_status": rec.get("status"),
                "elapsed_seconds": rec.get("elapsed_seconds"),
                "continuity_state": rec.get("continuity_state"),
                "progress_24h_pct": rec.get("progress_24h_pct"),
                "progress_72h_pct": rec.get("progress_72h_pct"),
                "live_capital_state": risk.get("live_capital_state"),
                "authorized_live_capital_usd": 0.0,
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(2.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
