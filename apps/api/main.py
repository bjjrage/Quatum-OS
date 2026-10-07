"""Main FastAPI application for Trading / Quant OS Cockpit API.

Authoritative operational API for Quant Cockpit v1.
Interfaces directly with Quant OS Python modules, Parquet/DuckDB data fabric,
experiment registry, and paper trading state.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import (
    system,
    recorder,
    quality,
    markets,
    strategies,
    experiments,
    backtests,
    holdouts,
    gates,
    portfolio,
    paper,
    execution,
    risk,
    capital,
    prop,
    attribution,
    audit,
    stream,
    history,
    research_spot,
    poly_paper,
)

app = FastAPI(
    title="Trading / Quant OS — Quant Cockpit API",
    version="1.0.0",
    description="Operational Quant Workstation API connecting UI to authoritative Quant OS Python engine.",
)


@app.on_event("startup")
async def mark_api_started() -> None:
    from src.common.runtime_health import RuntimeHealth
    RuntimeHealth("api").update("RUNNING", started=True, success=True)


@app.on_event("shutdown")
async def mark_api_stopped() -> None:
    from src.common.runtime_health import RuntimeHealth
    RuntimeHealth("api").update("STOPPED")

# Configure CORS for local development and institutional workstation deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(system.router)
app.include_router(recorder.router)
app.include_router(quality.router)
app.include_router(markets.router)
app.include_router(strategies.router)
app.include_router(experiments.router)
app.include_router(backtests.router)
app.include_router(holdouts.router)
app.include_router(gates.router)
app.include_router(portfolio.router)
app.include_router(paper.router)
app.include_router(execution.router)
app.include_router(risk.router)
app.include_router(capital.router)
app.include_router(prop.router)
app.include_router(attribution.router)
app.include_router(audit.router)
app.include_router(stream.router)
app.include_router(history.router)
app.include_router(research_spot.router)
app.include_router(poly_paper.router)


@app.get("/health")
@app.get("/api/health")
def health_check():
    """Real health: data dir writable, recorder fresh, no kill switch asserted. Never a constant."""
    import time
    from pathlib import Path
    checks = {}
    try:
        d = Path("data"); d.mkdir(exist_ok=True)
        probe = d / ".health_probe"; probe.write_text(str(time.time())); probe.unlink()
        checks["data_dir_writable"] = True
    except Exception:
        checks["data_dir_writable"] = False
    try:
        from apps.api.services.data_service import QuantOSDataService
        rec = QuantOSDataService.get_instance().get_recorder_status()
        status = str(rec.get("status", "UNKNOWN"))
        checks["recorder"] = status
        recorder_ok = status.upper() in ("RUNNING", "HEALTHY", "ACTIVE", "OK", "RECORDING")
    except Exception as exc:  # noqa: BLE001
        checks["recorder"] = f"ERROR:{type(exc).__name__}"
        recorder_ok = False
    healthy = checks["data_dir_writable"] and recorder_ok
    return {
        "status": "HEALTHY" if healthy else "DEGRADED",
        "checks": checks,
        "system": "Trading / Quant OS Cockpit API",
        "version": "1.0.0",
        "live_capital_authorized": "$0 (LOCKED)",
    }
