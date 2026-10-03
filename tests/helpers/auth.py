"""
Test-only authentication and authorization helpers for unit testing execution plane components.

IMPORTANT: This module is for testing harnesses only and MUST NEVER be imported by production code.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from src.execution_plane.authority import (
    ExecutionAuthorization,
    ExecutionAuthorizationSigner,
    ExecutionAuthorizationVerifier,
)
from src.execution_plane.models import ExecutionMode
from src.risk.engine import RiskDecision


def create_test_signer_and_verifier() -> Tuple[ExecutionAuthorizationSigner, ExecutionAuthorizationVerifier]:
    """Create a paired test signer and verifier."""
    signer = ExecutionAuthorizationSigner()
    return signer, signer.verifier


def mint_test_authorization(
    signer: Optional[ExecutionAuthorizationSigner] = None,
    kind: str = "SUBMIT",
    venue: str = "binance_perp",
    client_order_id: Optional[str] = "test-order-1",
    symbol: Optional[str] = "BTCUSDT",
    side: Optional[str] = "BUY",
    mode: ExecutionMode = ExecutionMode.SANDBOX,
    authorized_live_capital_usd: float = 0.0,
    risk_approved: bool = True,
    current_time_ns: Optional[int] = None,
    validity_window_ns: int = 3_600_000_000_000,
    intent_id: Optional[str] = "test-intent-1",
) -> ExecutionAuthorization:
    """Test helper for unit tests to mint a valid authorization with a mock RiskDecision."""
    s = signer or ExecutionAuthorizationSigner()
    decision = RiskDecision(approved=risk_approved, reason="Test harness authorization")
    return s.mint(
        kind=kind,
        venue=venue,
        mode=mode,
        client_order_id=client_order_id,
        intent_id=intent_id,
        symbol=symbol,
        side=side,
        risk_decision=decision,
        authorized_live_capital_usd=authorized_live_capital_usd,
        current_time_ns=current_time_ns,
        validity_window_ns=validity_window_ns,
    )


def issue_permit(
    kind: str,
    venue: str,
    client_order_id: Optional[str],
    mode: ExecutionMode,
    authorized_live_capital_usd: float,
    risk_approved: bool,
    issued_ns: int,
    symbol: Optional[str] = None,
    signer: Optional[ExecutionAuthorizationSigner] = None,
) -> ExecutionAuthorization:
    """Legacy test-only wrapper to create test permits."""
    return mint_test_authorization(
        signer=signer,
        kind=kind,
        venue=venue,
        client_order_id=client_order_id,
        symbol=symbol,
        mode=mode,
        authorized_live_capital_usd=authorized_live_capital_usd,
        risk_approved=risk_approved,
        current_time_ns=issued_ns,
        validity_window_ns=0,
    )
