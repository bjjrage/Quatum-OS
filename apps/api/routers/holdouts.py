"""Cryptographic Holdout Dataset Sealing and Audit endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/holdouts", tags=["Holdouts"])


@router.get("")
def get_holdouts():
    svc = QuantOSDataService.get_instance()
    return svc.get_holdouts()
