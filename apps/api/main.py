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
)

app = FastAPI(
    title="Trading / Quant OS — Quant Cockpit API",
    version="1.0.0",
    description="Operational Quant Workstation API connecting UI to authoritative Quant OS Python engine.",
)

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


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "system": "Trading / Quant OS Cockpit API",
        "version": "1.0.0",
        "live_capital_authorized": "$0 (LOCKED)",
    }
