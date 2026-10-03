"""Immutable System Audit Trail endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])


@router.get("")
def get_audit_trail():
    svc = QuantOSDataService.get_instance()
    return svc.get_audit_trail()
