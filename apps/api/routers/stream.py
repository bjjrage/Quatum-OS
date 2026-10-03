"""Real-time SSE event stream endpoint for operational workstation."""
import asyncio
import json
import logging
import time
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from apps.api.auth import verify_stream_auth, scrub_secrets
from apps.api.services.data_service import QuantOSDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stream", tags=["Streaming"])


@router.get("/events")
async def stream_events(authorized: bool = Depends(verify_stream_auth)):
    """Server-Sent Events stream emitting heartbeats, recorder status, and risk state.
    
    Security:
    - Enforces stream authentication if configured.
    - Masks secrets and credentials.
    - Handles client disconnects cleanly without task leakage.
    """
    async def event_generator():
        svc = QuantOSDataService.get_instance()
        try:
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
                clean_payload = scrub_secrets(payload)
                yield f"data: {json.dumps(clean_payload)}\n\n"
                await asyncio.sleep(2.0)
        except (asyncio.CancelledError, GeneratorExit):
            # Client disconnected gracefully
            return
        except Exception as e:
            logger.error("SSE stream error: %s", e)
            err_payload = {
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "ERROR",
                "message": "Stream interrupted fail-closed",
            }
            yield f"data: {json.dumps(err_payload)}\n\n"
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
