"""Markets and point-in-time tradability tier endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/markets", tags=["Markets"])


@router.get("/tradability")
def get_tradability():
    svc = QuantOSDataService.get_instance()
    return svc.get_markets_tradability()
