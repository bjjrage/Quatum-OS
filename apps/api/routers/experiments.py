"""Research Experiment Registry explorer endpoints."""
from fastapi import APIRouter, HTTPException
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/experiments", tags=["Experiments"])


@router.get("")
def list_experiments():
    svc = QuantOSDataService.get_instance()
    return svc.get_experiments()


@router.get("/{experiment_id}")
def get_experiment(experiment_id: str):
    svc = QuantOSDataService.get_instance()
    exp = svc.get_experiment_detail(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return exp
