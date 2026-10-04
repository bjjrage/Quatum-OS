"""System and environment metadata endpoints."""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/status")
def get_status():
    svc = QuantOSDataService.get_instance()
    return svc.get_system_status()


@router.get("/git")
def get_git():
    svc = QuantOSDataService.get_instance()
    sha = svc._get_git_sha()
    branch = svc._get_git_branch()
    commits = svc._get_git_log(5)
    return {
        "status": "AVAILABLE",
        "git_sha": sha,
        "git_sha_short": sha[:7] if sha else "UNKNOWN",
        "branch": branch,
        "recent_commits": commits,
    }


@router.get("/ci")
def get_ci_status():
    svc = QuantOSDataService.get_instance()
    return {
        "status": "UNKNOWN",
        "ci_provider": "OFFLINE_TEST_SUITE",
        "passing_tests": None,
        "failing_tests": None,
        "duration_seconds": None,
        "github_actions_status": "UNKNOWN / NOT CONNECTED",
        "github_actions_reason": "No external CI credentials configured in offline operational workstation.",
    }


@router.get("/persistence")
def get_persistence_status():
    """Honest control-plane read model. Never reports remote success it did not verify."""
    from src.persistence.config import SupabaseConfig
    from src.persistence.domain import OWN_CAPITAL_BASELINE_USD, AUTHORIZED_LIVE_CAPITAL_USD
    cfg = SupabaseConfig.from_env()
    local_db = Path("data/control_plane/control_plane.db")
    local = {"status": "LOCAL_ONLY" if local_db.exists() else "NOT_AVAILABLE",
             "source": "LOCAL_PERSISTED", "path": str(local_db)}
    return {
        "remote": cfg.status(),
        "local": local,
        "data_source": "LOCAL_RUNTIME",
        "live_authorized_capital_usd": AUTHORIZED_LIVE_CAPITAL_USD,
        "own_capital_baseline_usd": OWN_CAPITAL_BASELINE_USD,
        "own_capital_state_kind": "HYPOTHETICAL",
    }


@router.post("/git/save")
def git_save(request: Request, message: str = "Quant OS: guardar versión", push: bool = True):
    """Run tests; if they pass, commit everything and push to GitHub with the PC's own credentials. Local only."""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Only available from the local machine.")
    from apps.api.services import git_save as gs
    return gs.start(message=message[:500], push=push)


@router.get("/git/save/status")
def git_save_status():
    from apps.api.services import git_save as gs
    return gs.status()
