"""Acceptance Gate state machine, duration gating, and runtime manifest management."""
from enum import Enum
import json
import os
from pathlib import Path
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


MIN_24H_SECONDS: float = 24.0 * 3600.0  # 86,400 seconds
MIN_72H_SECONDS: float = 72.0 * 3600.0  # 259,200 seconds


class AcceptanceState(str, Enum):
    """Formal states for the Batch 0 continuous recording acceptance lifecycle."""
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    CHECKPOINT_24H_READY = "CHECKPOINT_24H_READY"
    CHECKPOINT_24H_PASS = "CHECKPOINT_24H_PASS"
    CHECKPOINT_24H_FAIL = "CHECKPOINT_24H_FAIL"
    CHECKPOINT_72H_READY = "CHECKPOINT_72H_READY"
    CHECKPOINT_72H_PASS = "CHECKPOINT_72H_PASS"
    CHECKPOINT_72H_FAIL = "CHECKPOINT_72H_FAIL"


class GateDurationError(ValueError):
    """Raised when an acceptance checkpoint pass is attempted before required duration."""
    pass


class GateEvaluationResult(BaseModel):
    """Result of evaluating an acceptance gate."""
    gate_name: str
    status: str  # "PENDING", "PASS", "FAIL"
    elapsed_seconds: float
    required_seconds: float
    passed: bool
    reasons: List[str] = Field(default_factory=list)


def evaluate_duration_gate(
    gate_name: str,
    elapsed_seconds: float,
    metrics_pass: bool,
    reasons: Optional[List[str]] = None,
) -> GateEvaluationResult:
    """Strict evaluation of an acceptance gate enforcing duration requirements.
    
    If elapsed_seconds is less than required, the gate status is strictly PENDING
    regardless of metric values.
    """
    reasons_list = list(reasons or [])
    
    if gate_name == "24h":
        required = MIN_24H_SECONDS
    elif gate_name == "72h":
        required = MIN_72H_SECONDS
    else:
        raise ValueError(f"Unknown gate name: {gate_name}")

    if elapsed_seconds < required:
        reasons_list.append(
            f"Gate duration requirement not met: elapsed {elapsed_seconds:.1f}s < required {required:.1f}s."
        )
        return GateEvaluationResult(
            gate_name=gate_name,
            status="PENDING",
            elapsed_seconds=elapsed_seconds,
            required_seconds=required,
            passed=False,
            reasons=reasons_list,
        )

    # Required time has elapsed: evaluate metrics
    if metrics_pass:
        return GateEvaluationResult(
            gate_name=gate_name,
            status="PASS",
            elapsed_seconds=elapsed_seconds,
            required_seconds=required,
            passed=True,
            reasons=["All gate criteria and duration requirements successfully satisfied."],
        )
    else:
        return GateEvaluationResult(
            gate_name=gate_name,
            status="FAIL",
            elapsed_seconds=elapsed_seconds,
            required_seconds=required,
            passed=False,
            reasons=reasons_list,
        )


def validate_state_transition(
    current_state: AcceptanceState,
    target_state: AcceptanceState,
    elapsed_seconds: float,
) -> AcceptanceState:
    """Validate acceptance state machine transition with strict duration enforcement."""
    if target_state == AcceptanceState.CHECKPOINT_24H_PASS:
        if elapsed_seconds < MIN_24H_SECONDS:
            raise GateDurationError(
                f"Cannot transition to {target_state.value}: required duration is {MIN_24H_SECONDS:.0f}s (24h), "
                f"but elapsed time is only {elapsed_seconds:.1f}s."
            )

    if target_state == AcceptanceState.CHECKPOINT_72H_PASS:
        if elapsed_seconds < MIN_72H_SECONDS:
            raise GateDurationError(
                f"Cannot transition to {target_state.value}: required duration is {MIN_72H_SECONDS:.0f}s (72h), "
                f"but elapsed time is only {elapsed_seconds:.1f}s."
            )

    return target_state


class RuntimeManifest(BaseModel):
    """Manifest tracking live recorder process state and metadata."""
    run_id: str
    git_sha: str
    started_at_utc: str
    started_at_timestamp_ns: int
    pid: int
    config_fingerprint: str
    status: AcceptanceState
    heartbeat_at_utc: str
    venues: List[str]

    @classmethod
    def create_new(
        cls,
        pid: int,
        git_sha: str,
        config_fingerprint: str,
        venues: Optional[List[str]] = None,
        run_id_prefix: str = "run",
    ) -> "RuntimeManifest":
        """Instantiate a new runtime manifest for a starting recording session."""
        now_ns = time.time_ns()
        now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        date_str = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        run_id = f"{run_id_prefix}_{date_str}_{os.urandom(4).hex()}"
        
        default_venues = venues or ["polymarket", "deribit", "binance_perp"]

        return cls(
            run_id=run_id,
            git_sha=git_sha,
            started_at_utc=now_utc,
            started_at_timestamp_ns=now_ns,
            pid=pid,
            config_fingerprint=config_fingerprint,
            status=AcceptanceState.RUNNING,
            heartbeat_at_utc=now_utc,
            venues=default_venues,
        )

    def elapsed_seconds(self) -> float:
        """Calculate elapsed runtime in seconds."""
        now_ns = time.time_ns()
        return max(0.0, (now_ns - self.started_at_timestamp_ns) / 1e9)

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.heartbeat_at_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def save(self, filepath: Path = Path("data/runtime/current_run.json")) -> None:
        """Atomically persist manifest to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = filepath.parent / f".tmp_{filepath.name}_{os.getpid()}"
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
        os.replace(tmp_file, filepath)

    @classmethod
    def load(cls, filepath: Path = Path("data/runtime/current_run.json")) -> "RuntimeManifest":
        """Load manifest from JSON file."""
        if not filepath.exists():
            raise FileNotFoundError(f"Runtime manifest not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
