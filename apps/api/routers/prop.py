"""Prop Firm Rule Profiles, Monte Carlo Simulations, and Multi-Account Compliance endpoints."""
from fastapi import APIRouter
from apps.api.services.data_service import QuantOSDataService

router = APIRouter(prefix="/api/prop", tags=["Prop Firms"])


@router.get("/profiles")
def get_prop_profiles():
    svc = QuantOSDataService.get_instance()
    return svc.get_prop_profiles()


@router.get("/attempts")
def get_prop_attempts():
    return {
        "status": "HEALTHY",
        "kill_switch_rule": "5 consecutive failed evaluations triggers kill switch and returns strategy to RESEARCH/REVIEW.",
        "ineligible_combinations": [],
        "attempts": [],
    }


@router.get("/simulations")
def get_prop_simulations(strategy_id: str = "STR-002", provider_id: str = "AlphaFunding"):
    svc = QuantOSDataService.get_instance()
    # Runs the empirical simulator; returns PENDING / INSUFFICIENT DATA because empirical trade samples are <30
    return svc.get_prop_simulator_result(strategy_id, provider_id)


@router.get("/compliance")
def get_multi_account_compliance():
    """Multi-Account Compliance status per provider."""
    return [
        {
            "provider_name": "AlphaFunding",
            "multiple_accounts_allowed": True,
            "same_bot_allowed": True,
            "same_strategy_allowed": True,
            "same_bot_considered_copy_trading": False,
            "shared_account_restrictions": "MAX_3_ACCOUNTS_PER_USER",
            "cross_account_hedging_policy": "ALLOWED_ACROSS_DISTINCT_POCKETS",
            "written_evidence_status": "VERIFIED",
            "second_account_status": "PASS",
            "verified_contract_ref": "AF_TERMS_2026_SEC4",
        },
        {
            "provider_name": "GammaProp",
            "multiple_accounts_allowed": False,
            "same_bot_allowed": False,
            "same_strategy_allowed": False,
            "same_bot_considered_copy_trading": True,
            "shared_account_restrictions": "UNKNOWN",
            "cross_account_hedging_policy": "UNKNOWN",
            "written_evidence_status": "PENDING",
            "second_account_status": "PENDING",
            "verified_contract_ref": "NONE",
        },
    ]
