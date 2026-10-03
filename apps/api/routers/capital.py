"""Capital Pockets and Multi-Account Governance endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/capital-pockets", tags=["Capital"])


@router.get("")
def get_capital_pockets():
    svc = QuantOSDataService.get_instance()
    return svc.get_capital_pockets()
