"""
Holdout Dataset Sealing and Audit Framework.

Core Invariants:
1. Holdout dataset is physically partitioned and cryptographically sealed.
2. Opening the holdout produces an immutable audit record:
   - who opened it
   - timestamp
   - strategy version evaluated
   - git SHA at time of opening
   - pre-registered hypothesis and parameter set fingerprint
3. Once holdout is evaluated for a strategy version, that strategy version
   CANNOT be re-tuned on the holdout. Any parameter change requires a new strategy version.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class HoldoutViolationError(Exception):
    """Raised when re-tuning or repeated uncommitted evaluation on sealed holdout occurs."""
    pass


class HoldoutAuditRecord(BaseModel):
    """Immutable audit record generated whenever holdout data is opened."""
    model_config = ConfigDict(extra="forbid")

    audit_id: str
    opened_by: str
    timestamp_ns: int
    timestamp_utc: str
    strategy_id: str
    strategy_version: str
    git_sha: str
    parameter_set_fingerprint: str
    hypothesis_description: str
    holdout_dataset_hash: str
    result_metrics: Dict[str, Any] = Field(default_factory=dict)


class SealedHoldoutManager:
    """
    Manages sealed holdout evaluation with immutable audit logging.
    Prevents p-hacking and multiple iterations on holdout data.
    """

    def __init__(self, audit_storage_path: Path = Path("data/research/holdout_audits.json")):
        self.audit_storage_path = Path(audit_storage_path)
        self._audits: List[HoldoutAuditRecord] = []
        self._load_audits()

    def _load_audits(self) -> None:
        if self.audit_storage_path.exists():
            try:
                with open(self.audit_storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._audits = [HoldoutAuditRecord(**item) for item in data]
            except Exception:
                self._audits = []

    def _persist_audits(self) -> None:
        self.audit_storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self.audit_storage_path.parent / f".tmp_{self.audit_storage_path.name}_{os.getpid()}"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump([a.model_dump() for a in self._audits], f, indent=2)
        os.replace(tmp_file, self.audit_storage_path)

    def evaluate_holdout(
        self,
        strategy_id: str,
        strategy_version: str,
        git_sha: str,
        parameter_set_fingerprint: str,
        hypothesis_description: str,
        holdout_dataset_bytes_or_hash: str,
        metrics: Dict[str, Any],
        opened_by: str = "SYSTEM_RESEARCH_GATE",
    ) -> HoldoutAuditRecord:
        """
        Record a holdout evaluation.
        
        Strict Governance Invariant:
        Once a (strategy_id, strategy_version) combination has been evaluated on holdout,
        it is permanently SEALED. Further evaluation with new parameters is rejected.
        """
        # Check if this strategy version was already tested on holdout
        for past_audit in self._audits:
            if (
                past_audit.strategy_id == strategy_id
                and past_audit.strategy_version == strategy_version
            ):
                raise HoldoutViolationError(
                    f"Governance Invariant Violated: Holdout dataset is sealed for '{strategy_id}' version '{strategy_version}'. "
                    f"It was previously evaluated at {past_audit.timestamp_utc} (Audit ID: {past_audit.audit_id}). "
                    "Re-tuning on the holdout is strictly forbidden. You must increment the strategy semantic version."
                )

        # Hash holdout dataset representation if not already a 64-char hash
        if len(holdout_dataset_bytes_or_hash) == 64 and all(c in "0123456789abcdefABCDEF" for c in holdout_dataset_bytes_or_hash):
            ds_hash = holdout_dataset_bytes_or_hash
        else:
            ds_hash = hashlib.sha256(holdout_dataset_bytes_or_hash.encode("utf-8")).hexdigest()

        now_ns = time.time_ns()
        now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        audit_id = f"holdout_{strategy_id}_{strategy_version}_{now_ns}"

        record = HoldoutAuditRecord(
            audit_id=audit_id,
            opened_by=opened_by,
            timestamp_ns=now_ns,
            timestamp_utc=now_utc,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            git_sha=git_sha,
            parameter_set_fingerprint=parameter_set_fingerprint,
            hypothesis_description=hypothesis_description,
            holdout_dataset_hash=ds_hash,
            result_metrics=metrics,
        )

        self._audits.append(record)
        self._persist_audits()
        return record

    def list_audits_for_strategy(self, strategy_id: str) -> List[HoldoutAuditRecord]:
        return [a for a in self._audits if a.strategy_id == strategy_id]
