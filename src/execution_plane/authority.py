"""
Authoritative Execution Risk Authorization and Non-Forgeable Permit System.

Invariants:
- Minting authority (ExecutionAuthorizationSigner) is private to ExecutionRouter.
- Verifying capability (ExecutionAuthorizationVerifier) is consumer-only (no mint method).
- Direct instantiation of ExecutionAuthorization without _ISSUER token raises PermissionError.
- PaperBroker / Adapters receive ExecutionAuthorizationVerifier ONLY (no minting authority).
- Duck typing and raw RiskDecision objects are strictly rejected.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from src.execution_plane.models import ExecutionMode


_ISSUER = object()


@dataclass(frozen=True)
class ExecutionAuthorization:
    """Structurally and cryptographically verifiable authorization for mutating actions.
    
    Minted exclusively after an approved RiskDecision through ExecutionAuthorizationSigner.
    Bound to intent_id, client_order_id, venue, symbol, side, mode, kind, risk_decision_id,
    risk_decision_fingerprint, expires_at_ns, and single-use nonce.
    """
    kind: str  # SUBMIT | CANCEL | CANCEL_ALL
    venue: str
    client_order_id: Optional[str]
    mode: ExecutionMode
    authorized_live_capital_usd: float
    risk_approved: bool
    issued_ns: int
    intent_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    risk_decision_id: Optional[str] = None
    risk_decision_fingerprint: Optional[str] = None
    expires_at_ns: int = 0
    nonce: str = ""
    signature: str = ""
    _issuer: Any = None

    def __post_init__(self):
        if self._issuer is not _ISSUER:
            raise PermissionError("ExecutionAuthorization can only be created by ExecutionAuthorizationSigner")


SubmitPermit = ExecutionAuthorization


class ExecutionAuthorizationVerifier:
    """Read-only verifier for execution authorizations.
    
    Can only verify authorizations against cryptographic signatures, scope bindings,
    expiration, and anti-replay nonces. Cannot mint authorizations.
    """

    def __init__(self, secret_key: bytes):
        self._secret_key: bytes = secret_key
        self._consumed_nonces: set[str] = set()

    def _compute_signature(
        self,
        kind: str,
        venue: str,
        client_order_id: Optional[str],
        mode: ExecutionMode,
        authorized_live_capital_usd: float,
        risk_approved: bool,
        issued_ns: int,
        intent_id: Optional[str],
        symbol: Optional[str],
        side: Optional[str],
        risk_decision_id: Optional[str],
        risk_decision_fingerprint: Optional[str],
        expires_at_ns: int,
        nonce: str,
    ) -> str:
        payload = (
            f"{kind}:{venue}:{client_order_id or ''}:{mode.value}:{authorized_live_capital_usd:.4f}:"
            f"{risk_approved}:{issued_ns}:{intent_id or ''}:{symbol or ''}:{side or ''}:"
            f"{risk_decision_id or ''}:{risk_decision_fingerprint or ''}:{expires_at_ns}:{nonce}"
        )
        return hmac.new(self._secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(
        self,
        auth: Any,
        expected_venue: str,
        expected_kind: str = "SUBMIT",
        expected_symbol: Optional[str] = None,
        expected_side: Optional[str] = None,
        expected_client_order_id: Optional[str] = None,
        expected_mode: Optional[ExecutionMode] = None,
        current_time_ns: Optional[int] = None,
    ) -> None:
        """Verify authorization validity, cryptographic signature, scope binding, expiration, and replay."""
        # 1. Type verification: absolutely no duck typing
        if not isinstance(auth, ExecutionAuthorization):
            raise PermissionError("Authorization rejected: invalid object type (duck typing strictly prohibited).")

        # 2. Risk approval check
        if not auth.risk_approved:
            raise PermissionError("Authorization rejected: risk_approved is False.")

        # 3. Cryptographic signature check
        expected_sig = self._compute_signature(
            kind=auth.kind,
            venue=auth.venue,
            client_order_id=auth.client_order_id,
            mode=auth.mode,
            authorized_live_capital_usd=auth.authorized_live_capital_usd,
            risk_approved=auth.risk_approved,
            issued_ns=auth.issued_ns,
            intent_id=auth.intent_id,
            symbol=auth.symbol,
            side=auth.side,
            risk_decision_id=auth.risk_decision_id,
            risk_decision_fingerprint=auth.risk_decision_fingerprint,
            expires_at_ns=auth.expires_at_ns,
            nonce=auth.nonce,
        )
        if not hmac.compare_digest(auth.signature, expected_sig):
            raise PermissionError("Authorization rejected: invalid cryptographic signature (tampered or forged permit).")

        # 4. Scope bindings
        if auth.kind != expected_kind:
            raise PermissionError(f"Authorization scope mismatch: expected kind {expected_kind}, got {auth.kind}.")
        venue_matches = (auth.venue == expected_venue) or (
            expected_venue in ("SIM", "paper") and auth.venue in ("SIM", "paper")
        )
        if not venue_matches:
            raise PermissionError(f"Authorization venue mismatch: expected venue {expected_venue}, got {auth.venue}.")
        if expected_symbol is not None and auth.symbol is not None:
            sym_matches = (auth.symbol == expected_symbol) or (
                auth.symbol.replace("-", "") == expected_symbol.replace("-", "")
            )
            if not sym_matches:
                raise PermissionError(f"Authorization symbol mismatch: expected symbol {expected_symbol}, got {auth.symbol}.")
        if expected_side is not None and auth.side is not None:
            if auth.side != expected_side:
                raise PermissionError(f"Authorization side mismatch: expected side {expected_side}, got {auth.side}.")
        if expected_client_order_id is not None and auth.client_order_id not in (None, expected_client_order_id):
            raise PermissionError(f"Authorization client_order_id mismatch: expected {expected_client_order_id}, got {auth.client_order_id}.")
        if expected_mode is not None and auth.mode != expected_mode:
            raise PermissionError(f"Authorization mode mismatch: expected {expected_mode}, got {auth.mode}.")

        # 5. Expiration check
        now_ns = current_time_ns if current_time_ns is not None else time.time_ns()
        if auth.expires_at_ns > 0 and now_ns > auth.expires_at_ns:
            raise PermissionError(f"Authorization expired: current_time_ns={now_ns} > expires_at_ns={auth.expires_at_ns}.")

        # 6. Replay protection
        if auth.nonce in self._consumed_nonces:
            raise PermissionError(f"Authorization rejected: permit token already consumed (replay detected, nonce={auth.nonce}).")
        self._consumed_nonces.add(auth.nonce)


class ExecutionAuthorizationSigner:
    """Authority for minting tamper-evident, non-reusable execution permits.
    
    Exclusively available to ExecutionRouter.
    """

    def __init__(
        self,
        secret_key: Optional[bytes] = None,
        default_validity_window_ns: int = 10_000_000_000,
    ):
        self._secret_key: bytes = secret_key or secrets.token_bytes(32)
        self.default_validity_window_ns: int = default_validity_window_ns  # 10s default
        self._verifier: ExecutionAuthorizationVerifier = ExecutionAuthorizationVerifier(secret_key=self._secret_key)

    @property
    def verifier(self) -> ExecutionAuthorizationVerifier:
        """Return the read-only verifier bound to this signer."""
        return self._verifier

    def mint(
        self,
        kind: str,
        venue: str,
        mode: ExecutionMode,
        client_order_id: Optional[str] = None,
        intent_id: Optional[str] = None,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        risk_decision: Optional[Any] = None,
        authorized_live_capital_usd: float = 0.0,
        current_time_ns: Optional[int] = None,
        validity_window_ns: Optional[int] = None,
    ) -> ExecutionAuthorization:
        """Mint a cryptographic, tamper-evident authorization token bound to an approved RiskDecision."""
        if risk_decision is None:
            raise PermissionError("ExecutionAuthorizationSigner: Cannot mint authorization without a RiskDecision.")

        if not getattr(risk_decision, "approved", False):
            violation = getattr(risk_decision, "violation_code", "UNKNOWN_VIOLATION")
            raise PermissionError(f"ExecutionAuthorizationSigner: RiskDecision rejected ({violation}). Minting prohibited.")

        now_ns = current_time_ns if current_time_ns is not None else time.time_ns()
        window_ns = validity_window_ns if validity_window_ns is not None else self.default_validity_window_ns
        expires_at_ns = (now_ns + window_ns) if window_ns > 0 else 0
        nonce = uuid.uuid4().hex

        # Compute risk decision fingerprint
        vcode = getattr(risk_decision.violation_code, "value", str(getattr(risk_decision, "violation_code", "")))
        reason = getattr(risk_decision, "reason", "")
        metrics = getattr(risk_decision, "metrics", {})
        metrics_repr = ",".join(f"{k}={v}" for k, v in sorted(metrics.items())) if isinstance(metrics, dict) else str(metrics)
        fp_raw = f"{risk_decision.approved}:{vcode}:{reason}:{metrics_repr}"
        risk_fp = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()
        risk_dec_id = getattr(risk_decision, "decision_id", None) or f"dec_{intent_id or nonce[:8]}"

        sig = self._verifier._compute_signature(
            kind=kind,
            venue=venue,
            client_order_id=client_order_id,
            mode=mode,
            authorized_live_capital_usd=authorized_live_capital_usd,
            risk_approved=True,
            issued_ns=now_ns,
            intent_id=intent_id,
            symbol=symbol,
            side=side,
            risk_decision_id=risk_dec_id,
            risk_decision_fingerprint=risk_fp,
            expires_at_ns=expires_at_ns,
            nonce=nonce,
        )

        return ExecutionAuthorization(
            kind=kind,
            venue=venue,
            client_order_id=client_order_id,
            mode=mode,
            authorized_live_capital_usd=authorized_live_capital_usd,
            risk_approved=True,
            issued_ns=now_ns,
            intent_id=intent_id,
            symbol=symbol,
            side=side,
            risk_decision_id=risk_dec_id,
            risk_decision_fingerprint=risk_fp,
            expires_at_ns=expires_at_ns,
            nonce=nonce,
            signature=sig,
            _issuer=_ISSUER,
        )
