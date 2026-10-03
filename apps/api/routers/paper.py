"""Realistic Paper Broker operational endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/paper", tags=["Paper Broker"])


@router.get("/account")
def get_paper_account():
    svc = QuantOSDataService.get_instance()
    return svc.get_paper_account()


@router.get("/orders")
def get_paper_orders():
    svc = QuantOSDataService.get_instance()
    acct = svc.get_paper_account()
    return acct.get("orders", [])


@router.get("/fills")
def get_paper_fills():
    svc = QuantOSDataService.get_instance()
    acct = svc.get_paper_account()
    return acct.get("fills", [])


@router.get("/positions")
def get_paper_positions():
    svc = QuantOSDataService.get_instance()
    acct = svc.get_paper_account()
    return acct.get("positions", [])
