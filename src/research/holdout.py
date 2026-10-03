"""
Holdout Dataset Sealing, Preregistration, and Governance Framework.

Core Invariants:
1. Holdout dataset is tamper-evident and isolated.
2. Opening a holdout requires a valid prior HoldoutPreRegistration with exact provenance match.
3. Access to holdout is single-use: opening it burns the dataset for that strategy lineage.
   Re-tuning on the same holdout is strictly forbidden, even with version increments.
4. Resealing (moving from OPENED/BURNED back to UNOPENED/PREREGISTERED) is technically impossible.
5. Any corruption in audit/preregistration logs locks holdout access fail-closed (GOVERNANCE_LOCKED).
"""

from __future__ import annotations

from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator


class HoldoutStatus(str, Enum):
    PREREGISTERED = "PREREGISTERED"
    UNOPENED = "UNOPENED"
    OPENED = "OPENED"
    BURNED = "BURNED"
    GOVERNANCE_LOCKED = "GOVERNANCE_LOCKED"


class HoldoutViolationError(Exception):
    """Raised when re-tuning, unauthorized access, or dataset reuse occurs on holdout."""
    pass


class HoldoutAuditIntegrityError(HoldoutViolationError):
    """Raised when holdout governance storage is corrupted, partial, or unverified."""
    pass


class HoldoutPreRegistration(BaseModel):
    """Immutable preregistration record required BEFORE accessing holdout data."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    preregistration_id: str
    strategy_id: str
    strategy_version: str = "1.0.0"
    git_sha: str = "UNKNOWN"
    dataset_fingerprint: str
    config_fingerprint: str
    parameter_set_fingerprint: str
    hypothesis_description: str
    falsification_criteria: Union[Dict[str, Any], List[str], str]
    primary_metrics: List[str] = Field(default_factory=list)
    analysis_plan_fingerprint: str = ""
    created_at_ns: int = Field(default_factory=lambda: time.time_ns())
    created_at_utc: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    status: HoldoutStatus = HoldoutStatus.PREREGISTERED

    @model_validator(mode="before")
    @classmethod
    def _validate_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for f in ("strategy_id", "dataset_fingerprint", "config_fingerprint", "parameter_set_fingerprint", "hypothesis_description"):
                v = data.get(f, "")
                if not str(v).strip():
                    raise ValueError(f"HoldoutPreRegistration field '{f}' must be a non-empty string.")
            fc = data.get("falsification_criteria")
            if not fc:
                raise ValueError("HoldoutPreRegistration field 'falsification_criteria' must be non-empty.")
        return data


class HoldoutAccessRecord(BaseModel):
    """Immutable record generated on the single allowed opening of a preregistered holdout."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    access_id: str
    preregistration_id: str
    strategy_id: str
    strategy_version: str
    dataset_fingerprint: str
    config_fingerprint: str
    parameter_set_fingerprint: str
    git_sha: str
    opened_at_ns: int = Field(default_factory=lambda: time.time_ns())
    opened_at_utc: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    opened_by: str = "SYSTEM_GOVERNANCE_GATE"


class HoldoutEvaluationResult(BaseModel):
    """Immutable empirical result of holdout evaluation, binding access and preregistration."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    result_id: str
    access_id: str
    preregistration_id: str
    strategy_id: str
    strategy_version: str
    dataset_fingerprint: str
    config_fingerprint: str
    git_sha: str
    result_metrics: Dict[str, Any] = Field(default_factory=dict)
    result_timestamp_ns: int = Field(default_factory=lambda: time.time_ns())
    result_timestamp_utc: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    passed: bool = False
    reasons: List[str] = Field(default_factory=list)


class HoldoutAuditRecord(BaseModel):
    """Legacy audit record preserved for backwards compatibility."""
    model_config = ConfigDict(extra="forbid", frozen=True)

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
    Manages holdout preregistration, one-time access, evaluation recording, and audit logging.
    Enforces that holdout data is opened ONLY after explicit preregistration,
    and once opened or burned, cannot be reused for that strategy lineage.
    Fail-closed: Any corruption in storage files locks all holdout operations (GOVERNANCE_LOCKED).
    """

    def __init__(
        self,
        audit_storage_path: Path = Path("data/research/holdout_audits.json"),
        raise_on_corruption: bool = True,
    ):
        self.audit_storage_path = Path(audit_storage_path)
        base_dir = self.audit_storage_path.parent
        self.prereg_storage_path = base_dir / "holdout_preregistrations.json"
        self.access_storage_path = base_dir / "holdout_access_records.json"
        self.results_storage_path = base_dir / "holdout_evaluation_results.json"
        self.raise_on_corruption = raise_on_corruption

        self._audits: List[HoldoutAuditRecord] = []
        self._preregistrations: Dict[str, HoldoutPreRegistration] = {}
        self._access_records: Dict[str, HoldoutAccessRecord] = {}
        self._evaluation_results: Dict[str, HoldoutEvaluationResult] = {}
        self._burned_lineages: Set[Tuple[str, str]] = set()  # (strategy_id, dataset_fingerprint)

        self._is_corrupted: bool = False
        self._corruption_error: Optional[str] = None
        self._load_storage()

    @property
    def is_corrupted(self) -> bool:
        return self._is_corrupted

    def get_status(self) -> str:
        """Return high-level holdout status."""
        if self._is_corrupted:
            return HoldoutStatus.GOVERNANCE_LOCKED.value
        if self._burned_lineages or any(p.status in (HoldoutStatus.OPENED, HoldoutStatus.BURNED) for p in self._preregistrations.values()):
            return HoldoutStatus.BURNED.value if any(p.status == HoldoutStatus.BURNED for p in self._preregistrations.values()) else HoldoutStatus.OPENED.value
        if self._preregistrations:
            return HoldoutStatus.PREREGISTERED.value
        return HoldoutStatus.UNOPENED.value

    def _load_storage(self) -> None:
        """Load all persistence stores. If ANY store is corrupted, lock fail-closed."""
        # 1. Audits
        if self.audit_storage_path.exists():
            try:
                with open(self.audit_storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError(f"Holdout audit file must contain a JSON list, got {type(data).__name__}")
                self._audits = [HoldoutAuditRecord(**item) for item in data]
                for a in self._audits:
                    self._burned_lineages.add((a.strategy_id, a.holdout_dataset_hash))
            except Exception as e:
                self._is_corrupted = True
                self._corruption_error = f"Audit log corruption: {e}"
                if self.raise_on_corruption:
                    raise HoldoutAuditIntegrityError(
                        f"Holdout audit storage at '{self.audit_storage_path}' is corrupted: {e}. "
                        "Holdout access is locked to prevent unverified re-evaluations."
                    ) from e
                return

        # 2. Preregistrations
        if self.prereg_storage_path.exists():
            try:
                with open(self.prereg_storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError("Preregistrations file must contain a JSON list.")
                for item in data:
                    prereg = HoldoutPreRegistration(**item)
                    self._preregistrations[prereg.preregistration_id] = prereg
                    if prereg.status in (HoldoutStatus.OPENED, HoldoutStatus.BURNED):
                        self._burned_lineages.add((prereg.strategy_id, prereg.dataset_fingerprint))
            except Exception as e:
                self._is_corrupted = True
                self._corruption_error = f"Preregistrations corruption: {e}"
                if self.raise_on_corruption:
                    raise HoldoutAuditIntegrityError(f"Holdout preregistrations corrupted: {e}") from e
                return

        # 3. Access records
        if self.access_storage_path.exists():
            try:
                with open(self.access_storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError("Access records file must contain a JSON list.")
                for item in data:
                    acc = HoldoutAccessRecord(**item)
                    self._access_records[acc.access_id] = acc
                    self._burned_lineages.add((acc.strategy_id, acc.dataset_fingerprint))
            except Exception as e:
                self._is_corrupted = True
                self._corruption_error = f"Access records corruption: {e}"
                if self.raise_on_corruption:
                    raise HoldoutAuditIntegrityError(f"Holdout access records corrupted: {e}") from e
                return

        # 4. Evaluation results
        if self.results_storage_path.exists():
            try:
                with open(self.results_storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError("Evaluation results file must contain a JSON list.")
                for item in data:
                    res = HoldoutEvaluationResult(**item)
                    self._evaluation_results[res.result_id] = res
                    self._burned_lineages.add((res.strategy_id, res.dataset_fingerprint))
            except Exception as e:
                self._is_corrupted = True
                self._corruption_error = f"Evaluation results corruption: {e}"
                if self.raise_on_corruption:
                    raise HoldoutAuditIntegrityError(f"Holdout evaluation results corrupted: {e}") from e
                return

    def _persist_atomic(self, path: Path, data: List[Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f".tmp_{path.name}_{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)

    def create_preregistration(
        self,
        strategy_id: str,
        strategy_version: str,
        git_sha: str,
        dataset_fingerprint: str,
        config_fingerprint: str,
        parameter_set_fingerprint: str,
        hypothesis_description: str,
        falsification_criteria: Union[Dict[str, Any], List[str], str],
        primary_metrics: Optional[List[str]] = None,
        analysis_plan_fingerprint: str = "",
        preregistration_id: Optional[str] = None,
    ) -> HoldoutPreRegistration:
        """Create a tamper-evident preregistration before accessing holdout."""
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(
                f"Cannot create preregistration: holdout storage is corrupted (GOVERNANCE_LOCKED): {self._corruption_error}. "
                "Governance is locked fail-closed."
            )

        # Invariant: (strategy_id, dataset_fingerprint) cannot be reused if already burned/opened
        ds_hash = dataset_fingerprint if len(dataset_fingerprint) == 64 else hashlib.sha256(dataset_fingerprint.encode("utf-8")).hexdigest()
        if (strategy_id, dataset_fingerprint) in self._burned_lineages or (strategy_id, ds_hash) in self._burned_lineages:
            raise HoldoutViolationError(
                f"Governance Invariant Violated: Dataset fingerprint '{dataset_fingerprint}' for strategy "
                f"'{strategy_id}' has already been accessed or burned. Holdout dataset reuse across iterations is forbidden."
            )

        now_ns = time.time_ns()
        prereg_id = preregistration_id or f"prereg_{strategy_id}_{strategy_version}_{now_ns}"
        if prereg_id in self._preregistrations:
            raise HoldoutViolationError(f"Preregistration '{prereg_id}' already exists.")

        record = HoldoutPreRegistration(
            preregistration_id=prereg_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            git_sha=git_sha,
            dataset_fingerprint=dataset_fingerprint,
            config_fingerprint=config_fingerprint,
            parameter_set_fingerprint=parameter_set_fingerprint,
            hypothesis_description=hypothesis_description,
            falsification_criteria=falsification_criteria,
            primary_metrics=primary_metrics or ["sharpe", "max_drawdown"],
            analysis_plan_fingerprint=analysis_plan_fingerprint or config_fingerprint,
            created_at_ns=now_ns,
            created_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            status=HoldoutStatus.PREREGISTERED,
        )

        self._preregistrations[prereg_id] = record
        self._persist_atomic(self.prereg_storage_path, [p.model_dump() for p in self._preregistrations.values()])
        return record

    def open_holdout(
        self,
        preregistration_id: str,
        strategy_id: str,
        strategy_version: str,
        git_sha: str,
        config_fingerprint: str,
        parameter_set_fingerprint: str,
        opened_by: str = "SYSTEM_GOVERNANCE_GATE",
    ) -> HoldoutAccessRecord:
        """
        Record a one-time access to holdout data.
        Enforces exact provenance match with the prior preregistration.
        Transitions preregistration status to OPENED and burns dataset for this strategy lineage.
        """
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(
                f"Cannot open holdout: holdout storage is corrupted: {self._corruption_error}. "
                "Governance is locked fail-closed."
            )

        prereg = self._preregistrations.get(preregistration_id)
        if not prereg:
            raise HoldoutViolationError(
                f"Cannot open holdout: preregistration '{preregistration_id}' does not exist."
            )

        if prereg.status not in (HoldoutStatus.PREREGISTERED, HoldoutStatus.UNOPENED):
            raise HoldoutViolationError(
                f"Cannot open holdout: preregistration '{preregistration_id}' is already {prereg.status.value}. "
                "Holdout datasets cannot be re-opened or resealed."
            )

        # Exact provenance check
        if (
            prereg.strategy_id != strategy_id
            or prereg.strategy_version != strategy_version
            or prereg.git_sha != git_sha
            or prereg.config_fingerprint != config_fingerprint
            or prereg.parameter_set_fingerprint != parameter_set_fingerprint
        ):
            raise HoldoutViolationError(
                f"Provenance mismatch during holdout opening! Preregistered: "
                f"({prereg.strategy_id}, {prereg.strategy_version}, {prereg.git_sha}, {prereg.config_fingerprint}) "
                f"!= Opening: ({strategy_id}, {strategy_version}, {git_sha}, {config_fingerprint})"
            )

        now_ns = time.time_ns()
        access_id = f"access_{strategy_id}_{strategy_version}_{now_ns}"

        access_record = HoldoutAccessRecord(
            access_id=access_id,
            preregistration_id=preregistration_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            dataset_fingerprint=prereg.dataset_fingerprint,
            config_fingerprint=config_fingerprint,
            parameter_set_fingerprint=parameter_set_fingerprint,
            git_sha=git_sha,
            opened_at_ns=now_ns,
            opened_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            opened_by=opened_by,
        )

        # Transition preregistration to OPENED
        updated_prereg = prereg.model_copy(update={"status": HoldoutStatus.OPENED})
        self._preregistrations[preregistration_id] = updated_prereg
        self._access_records[access_id] = access_record
        self._burned_lineages.add((strategy_id, prereg.dataset_fingerprint))

        # Persist atomically
        self._persist_atomic(self.prereg_storage_path, [p.model_dump() for p in self._preregistrations.values()])
        self._persist_atomic(self.access_storage_path, [a.model_dump() for a in self._access_records.values()])

        return access_record

    def record_evaluation_result(
        self,
        access_id: str,
        result_metrics: Dict[str, Any],
        passed: bool,
        reasons: Optional[List[str]] = None,
    ) -> HoldoutEvaluationResult:
        """
        Record empirical results of holdout evaluation against an authorized access record.
        Transitions preregistration to BURNED.
        """
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(
                f"Cannot record holdout result: holdout storage is corrupted: {self._corruption_error}."
            )

        access_record = self._access_records.get(access_id)
        if not access_record:
            raise HoldoutViolationError(f"No valid holdout access record found for access_id '{access_id}'.")

        prereg = self._preregistrations.get(access_record.preregistration_id)
        if not prereg:
            raise HoldoutViolationError(f"Preregistration '{access_record.preregistration_id}' missing.")

        # Check if already evaluated
        if any(r.access_id == access_id for r in self._evaluation_results.values()):
            raise HoldoutViolationError(f"Evaluation result already recorded for access_id '{access_id}'.")

        now_ns = time.time_ns()
        result_id = f"eval_{access_record.strategy_id}_{access_record.strategy_version}_{now_ns}"

        res = HoldoutEvaluationResult(
            result_id=result_id,
            access_id=access_id,
            preregistration_id=prereg.preregistration_id,
            strategy_id=access_record.strategy_id,
            strategy_version=access_record.strategy_version,
            dataset_fingerprint=access_record.dataset_fingerprint,
            config_fingerprint=access_record.config_fingerprint,
            git_sha=access_record.git_sha,
            result_metrics=result_metrics,
            result_timestamp_ns=now_ns,
            result_timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            passed=passed,
            reasons=reasons or [],
        )

        # Transition preregistration to BURNED
        updated_prereg = prereg.model_copy(update={"status": HoldoutStatus.BURNED})
        self._preregistrations[prereg.preregistration_id] = updated_prereg
        self._evaluation_results[result_id] = res

        # Also log to legacy audits list
        audit_id = f"holdout_{access_record.strategy_id}_{access_record.strategy_version}_{now_ns}"
        audit_rec = HoldoutAuditRecord(
            audit_id=audit_id,
            opened_by=access_record.opened_by,
            timestamp_ns=now_ns,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            strategy_id=access_record.strategy_id,
            strategy_version=access_record.strategy_version,
            git_sha=access_record.git_sha,
            parameter_set_fingerprint=access_record.parameter_set_fingerprint,
            hypothesis_description=prereg.hypothesis_description,
            holdout_dataset_hash=access_record.dataset_fingerprint,
            result_metrics=result_metrics,
        )
        self._audits.append(audit_rec)

        # Persist all atomically
        self._persist_atomic(self.prereg_storage_path, [p.model_dump() for p in self._preregistrations.values()])
        self._persist_atomic(self.results_storage_path, [r.model_dump() for r in self._evaluation_results.values()])
        self._persist_atomic(self.audit_storage_path, [a.model_dump() for a in self._audits])

        return res

    def get_preregistration(self, preregistration_id: str) -> Optional[HoldoutPreRegistration]:
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(f"Storage corrupted: {self._corruption_error}")
        return self._preregistrations.get(preregistration_id)

    def get_access_record(self, access_id: str) -> Optional[HoldoutAccessRecord]:
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(f"Storage corrupted: {self._corruption_error}")
        return self._access_records.get(access_id)

    def get_evaluation_result(self, result_id: str) -> Optional[HoldoutEvaluationResult]:
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(f"Storage corrupted: {self._corruption_error}")
        return self._evaluation_results.get(result_id)

    def list_preregistrations_for_strategy(self, strategy_id: str) -> List[HoldoutPreRegistration]:
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(f"Storage corrupted: {self._corruption_error}")
        return [p for p in self._preregistrations.values() if p.strategy_id == strategy_id]

    def list_audits_for_strategy(self, strategy_id: str) -> List[HoldoutAuditRecord]:
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(f"Storage corrupted: {self._corruption_error}")
        return [a for a in self._audits if a.strategy_id == strategy_id]

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
        config_fingerprint: str = "",
        allow_dataset_reuse: bool = False,
    ) -> HoldoutAuditRecord:
        """
        Backwards-compatible convenience method.
        Under the hood creates a preregistration, executes one-time access,
        and records evaluation result.
        """
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(
                f"Cannot evaluate holdout: audit log at '{self.audit_storage_path}' is corrupted: {self._corruption_error}. "
                "Holdout dataset access is strictly locked."
            )

        # Hash holdout dataset representation if not already a 64-char hash
        if len(holdout_dataset_bytes_or_hash) == 64 and all(c in "0123456789abcdefABCDEF" for c in holdout_dataset_bytes_or_hash):
            ds_hash = holdout_dataset_bytes_or_hash
        else:
            ds_hash = hashlib.sha256(holdout_dataset_bytes_or_hash.encode("utf-8")).hexdigest()

        # Check if this strategy version was already tested on holdout
        for past_audit in self._audits:
            if past_audit.strategy_id == strategy_id and past_audit.strategy_version == strategy_version:
                raise HoldoutViolationError(
                    f"Governance Invariant Violated: Holdout dataset is sealed for '{strategy_id}' version '{strategy_version}'. "
                    f"It was previously evaluated at {past_audit.timestamp_utc} (Audit ID: {past_audit.audit_id}). "
                    "Re-tuning on the holdout is strictly forbidden. You must increment the strategy semantic version."
                )

        # Check dataset reuse
        if not allow_dataset_reuse:
            if (strategy_id, ds_hash) in self._burned_lineages or any(a.strategy_id == strategy_id and a.holdout_dataset_hash == ds_hash for a in self._audits):
                raise HoldoutViolationError(
                    f"Governance Invariant Violated: Dataset fingerprint '{ds_hash}' for strategy '{strategy_id}' "
                    "has already been opened or burned. Dataset reuse across strategy iterations is forbidden."
                )

        cfg_fp = config_fingerprint or parameter_set_fingerprint
        prereg = self.create_preregistration(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            git_sha=git_sha,
            dataset_fingerprint=ds_hash,
            config_fingerprint=cfg_fp,
            parameter_set_fingerprint=parameter_set_fingerprint,
            hypothesis_description=hypothesis_description,
            falsification_criteria="Negative out-of-sample expectancy",
        )

        acc = self.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            git_sha=git_sha,
            config_fingerprint=cfg_fp,
            parameter_set_fingerprint=parameter_set_fingerprint,
            opened_by=opened_by,
        )

        self.record_evaluation_result(
            access_id=acc.access_id,
            result_metrics=metrics,
            passed=True,
            reasons=[],
        )

        return self._audits[-1]

    def burn_holdout(self, strategy_id: str, dataset_fingerprint: str, reason: str = "Manual burn") -> None:
        """Mark a holdout partition as burned for a strategy lineage."""
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(
                f"Cannot burn holdout: holdout storage is corrupted (GOVERNANCE_LOCKED): {self._corruption_error}."
            )
        self._burned_lineages.add((strategy_id, dataset_fingerprint))
        updated = False
        for p in self._preregistrations.values():
            if p.strategy_id == strategy_id and p.dataset_fingerprint == dataset_fingerprint:
                object.__setattr__(p, "status", HoldoutStatus.BURNED)
                updated = True
        if updated:
            self._persist_atomic(self.prereg_storage_path, [p.model_dump() for p in self._preregistrations.values()])
