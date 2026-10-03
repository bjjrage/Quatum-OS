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
import math
import os
from pathlib import Path
import re
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


FORBIDDEN_PROVENANCE_PLACEHOLDERS: Set[str] = {
    "unknown",
    "unspecified",
    "provenance_missing",
    "ds_prov_unspecified",
    "cfg_prov_unspecified",
    "provenance_unspecified",
    "none",
    "null",
    "undefined",
}


class HoldoutCriterionOperator(str, Enum):
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    EQ = "EQ"


class HoldoutAcceptanceCriterion(BaseModel):
    """Machine-evaluable acceptance criterion preregistered before holdout access."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_name: str
    operator: HoldoutCriterionOperator
    threshold: float

    @model_validator(mode="before")
    @classmethod
    def _validate(cls, data: Any) -> Any:
        if isinstance(data, dict):
            m = str(data.get("metric_name", "")).strip()
            if not m:
                raise ValueError("HoldoutAcceptanceCriterion 'metric_name' must be a non-empty string.")
            op = data.get("operator")
            if isinstance(op, str):
                op_norm = op.strip().upper()
                op_map = {
                    ">": HoldoutCriterionOperator.GT,
                    "GT": HoldoutCriterionOperator.GT,
                    ">=": HoldoutCriterionOperator.GTE,
                    "GTE": HoldoutCriterionOperator.GTE,
                    "<": HoldoutCriterionOperator.LT,
                    "LT": HoldoutCriterionOperator.LT,
                    "<=": HoldoutCriterionOperator.LTE,
                    "LTE": HoldoutCriterionOperator.LTE,
                    "==": HoldoutCriterionOperator.EQ,
                    "=": HoldoutCriterionOperator.EQ,
                    "EQ": HoldoutCriterionOperator.EQ,
                }
                if op_norm not in op_map:
                    raise ValueError(f"Unsupported operator '{op}'. Supported: GT (>), GTE (>=), LT (<), LTE (<=), EQ (==).")
                data["operator"] = op_map[op_norm]
            thresh = data.get("threshold")
            if thresh is None or not isinstance(thresh, (int, float)) or isinstance(thresh, bool):
                raise ValueError(f"HoldoutAcceptanceCriterion 'threshold' must be a numeric float, got {thresh}")
            if math.isnan(float(thresh)) or math.isinf(float(thresh)):
                raise ValueError(f"HoldoutAcceptanceCriterion 'threshold' must be finite, got {thresh}")
            data["threshold"] = float(thresh)
            data["metric_name"] = m
        return data


class HoldoutCriterionResult(BaseModel):
    """Machine-evaluable result for a single preregistered criterion."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_name: str
    observed_value: Optional[float] = None
    operator: HoldoutCriterionOperator
    threshold: float
    passed: bool
    reason: Optional[str] = None


def _parse_falsification_criteria(
    criteria: Union[Dict[str, Any], List[str], str]
) -> List[HoldoutAcceptanceCriterion]:
    results: List[HoldoutAcceptanceCriterion] = []
    items: List[str] = []
    if isinstance(criteria, str):
        items = [criteria]
    elif isinstance(criteria, list):
        items = [str(x) for x in criteria]
    elif isinstance(criteria, dict):
        for k, v in criteria.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                results.append(
                    HoldoutAcceptanceCriterion(
                        metric_name=k.strip().lower().replace(" ", "_"),
                        operator=HoldoutCriterionOperator.GTE,
                        threshold=float(v),
                    )
                )

    for item in items:
        m = re.match(
            r"^\s*([A-Za-z0-9_ ]+?)\s*(<=|>=|<|>|==|=)\s*([0-9.]+)\s*(%?)\s*$",
            item.strip(),
        )
        if m:
            raw_metric, op, raw_val, is_pct = m.groups()
            metric_name = raw_metric.strip().lower().replace(" ", "_")
            val = float(raw_val)
            if is_pct == "%" and val > 1.0:
                val = val / 100.0
            # Falsification condition is when the strategy FAILS.
            # Thus, acceptance condition is the logical negation of falsification:
            inverted_ops = {
                "<": HoldoutCriterionOperator.GTE,
                "<=": HoldoutCriterionOperator.GT,
                ">": HoldoutCriterionOperator.LTE,
                ">=": HoldoutCriterionOperator.LT,
                "==": HoldoutCriterionOperator.EQ,
                "=": HoldoutCriterionOperator.EQ,
            }
            inv_op = inverted_ops.get(op)
            if inv_op:
                results.append(
                    HoldoutAcceptanceCriterion(
                        metric_name=metric_name,
                        operator=inv_op,
                        threshold=val,
                    )
                )
    return results


class HoldoutPreRegistration(BaseModel):
    """Immutable preregistration record required BEFORE accessing holdout data."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    preregistration_id: str
    strategy_id: str
    strategy_version: str
    git_sha: str
    dataset_fingerprint: str
    config_fingerprint: str
    parameter_set_fingerprint: str
    hypothesis_description: str
    falsification_criteria: Union[Dict[str, Any], List[str], str]
    primary_metrics: List[str]
    analysis_plan_fingerprint: str
    acceptance_criteria: List[HoldoutAcceptanceCriterion] = Field(default_factory=list)
    created_at_ns: int = Field(default_factory=lambda: time.time_ns())
    created_at_utc: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    status: HoldoutStatus = HoldoutStatus.PREREGISTERED

    @model_validator(mode="before")
    @classmethod
    def _validate_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            required_str_fields = (
                "strategy_id",
                "strategy_version",
                "git_sha",
                "dataset_fingerprint",
                "config_fingerprint",
                "parameter_set_fingerprint",
                "hypothesis_description",
                "analysis_plan_fingerprint",
            )
            for f in required_str_fields:
                v = data.get(f, "")
                if not str(v).strip():
                    raise ValueError(f"HoldoutPreRegistration field '{f}' must be a non-empty string.")
                if str(v).strip().lower() in FORBIDDEN_PROVENANCE_PLACEHOLDERS:
                    raise ValueError(
                        f"HoldoutPreRegistration field '{f}' contains prohibited placeholder '{v}'."
                    )
            fc = data.get("falsification_criteria")
            if not fc:
                raise ValueError("HoldoutPreRegistration field 'falsification_criteria' must be non-empty.")
            pm = data.get("primary_metrics")
            if not pm or not isinstance(pm, list) or len(pm) == 0:
                raise ValueError("HoldoutPreRegistration field 'primary_metrics' must be an explicitly preregistered non-empty list.")
            ac = data.get("acceptance_criteria")
            if ac is not None and isinstance(ac, list):
                data["acceptance_criteria"] = [
                    c if isinstance(c, HoldoutAcceptanceCriterion) else HoldoutAcceptanceCriterion(**c)
                    for c in ac
                ]
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
    criterion_results: List[HoldoutCriterionResult] = Field(default_factory=list)
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
        primary_metrics: List[str],
        analysis_plan_fingerprint: str,
        preregistration_id: Optional[str] = None,
        acceptance_criteria: Optional[List[Union[HoldoutAcceptanceCriterion, Dict[str, Any]]]] = None,
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

        criteria_to_store: List[HoldoutAcceptanceCriterion] = []
        if acceptance_criteria is not None:
            if not isinstance(acceptance_criteria, list) or len(acceptance_criteria) == 0:
                raise ValueError("HoldoutPreRegistration acceptance_criteria must be a non-empty list when explicitly specified.")
            for item in acceptance_criteria:
                if isinstance(item, HoldoutAcceptanceCriterion):
                    criteria_to_store.append(item)
                elif isinstance(item, dict):
                    criteria_to_store.append(HoldoutAcceptanceCriterion(**item))
                else:
                    raise TypeError(f"Expected HoldoutAcceptanceCriterion or dict, got {type(item).__name__}")
        else:
            criteria_to_store = _parse_falsification_criteria(falsification_criteria)

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
            primary_metrics=primary_metrics,
            analysis_plan_fingerprint=analysis_plan_fingerprint,
            acceptance_criteria=criteria_to_store,
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
        reasons: Optional[List[str]] = None,
        *args,
        **kwargs,
    ) -> HoldoutEvaluationResult:
        """
        Record empirical results of holdout evaluation against an authorized access record.
        Pass/fail status is deterministically derived from preregistered acceptance criteria.
        Caller-supplied 'passed' boolean is strictly forbidden to prevent authority bypass.
        Transitions preregistration to BURNED.
        """
        if args or "passed" in kwargs:
            raise ValueError(
                "CALLER_SUPPLIED_PASSED_FORBIDDEN: record_evaluation_result does not accept caller-supplied 'passed'. "
                "Holdout evaluation result is derived deterministically from preregistered acceptance criteria."
            )

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

        # Deterministic criteria derivation
        derived_passed = True
        criterion_results: List[HoldoutCriterionResult] = []
        eval_reasons: List[str] = list(reasons or [])

        if not prereg.acceptance_criteria:
            derived_passed = False
            eval_reasons.append("NO_PREREGISTERED_ACCEPTANCE_CRITERIA: Cannot evaluate holdout without machine-evaluable acceptance criteria.")

        metrics_lookup: Dict[str, Any] = {}
        for k, v in result_metrics.items():
            metrics_lookup[str(k).strip().lower().replace(" ", "_")] = v
            metrics_lookup[str(k).strip()] = v

        for crit in prereg.acceptance_criteria:
            crit_metric_norm = crit.metric_name.strip().lower().replace(" ", "_")
            if crit.metric_name in result_metrics:
                obs_raw = result_metrics[crit.metric_name]
            elif crit_metric_norm in metrics_lookup:
                obs_raw = metrics_lookup[crit_metric_norm]
            else:
                suffix_match = None
                for mk, mv in metrics_lookup.items():
                    if mk.endswith(f"_{crit_metric_norm}") or mk.endswith(crit_metric_norm):
                        suffix_match = mv
                        break
                if suffix_match is not None:
                    obs_raw = suffix_match
                else:
                    derived_passed = False
                    msg = f"REQUIRED_HOLDOUT_METRIC_MISSING: Preregistered metric '{crit.metric_name}' missing from result_metrics."
                    eval_reasons.append(msg)
                    criterion_results.append(
                        HoldoutCriterionResult(
                            metric_name=crit.metric_name,
                            observed_value=None,
                            operator=crit.operator,
                            threshold=crit.threshold,
                            passed=False,
                            reason=msg,
                        )
                    )
                    continue

            if obs_raw is None or isinstance(obs_raw, bool) or not isinstance(obs_raw, (int, float)):
                derived_passed = False
                msg = f"NON_FINITE_HOLDOUT_METRIC: Preregistered metric '{crit.metric_name}' value '{obs_raw}' is non-numeric."
                eval_reasons.append(msg)
                criterion_results.append(
                    HoldoutCriterionResult(
                        metric_name=crit.metric_name,
                        observed_value=None,
                        operator=crit.operator,
                        threshold=crit.threshold,
                        passed=False,
                        reason=msg,
                    )
                )
                continue

            obs_val = float(obs_raw)
            if math.isnan(obs_val) or math.isinf(obs_val):
                derived_passed = False
                msg = f"NON_FINITE_HOLDOUT_METRIC: Preregistered metric '{crit.metric_name}' value is non-finite: {obs_val}"
                eval_reasons.append(msg)
                criterion_results.append(
                    HoldoutCriterionResult(
                        metric_name=crit.metric_name,
                        observed_value=obs_val,
                        operator=crit.operator,
                        threshold=crit.threshold,
                        passed=False,
                        reason=msg,
                    )
                )
                continue

            op = crit.operator
            thresh = crit.threshold
            crit_pass = False
            if op == HoldoutCriterionOperator.GT:
                crit_pass = obs_val > thresh
            elif op == HoldoutCriterionOperator.GTE:
                crit_pass = obs_val >= thresh
            elif op == HoldoutCriterionOperator.LT:
                crit_pass = obs_val < thresh
            elif op == HoldoutCriterionOperator.LTE:
                crit_pass = obs_val <= thresh
            elif op == HoldoutCriterionOperator.EQ:
                crit_pass = abs(obs_val - thresh) <= 1e-9

            if not crit_pass:
                derived_passed = False
                crit_reason = f"CRITERION_BREACH: '{crit.metric_name}' observed {obs_val} does not satisfy {op.value} {thresh}"
                eval_reasons.append(crit_reason)
            else:
                crit_reason = None

            criterion_results.append(
                HoldoutCriterionResult(
                    metric_name=crit.metric_name,
                    observed_value=obs_val,
                    operator=crit.operator,
                    threshold=crit.threshold,
                    passed=crit_pass,
                    reason=crit_reason,
                )
            )

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
            passed=derived_passed,
            criterion_results=criterion_results,
            reasons=eval_reasons,
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

    def evaluate_holdout(self, *args, **kwargs) -> Any:
        """
        Legacy operational method disabled by Pre-Paper Hardening 03B.
        Holdout data evaluation must follow the explicit governance lifecycle:
        create_preregistration() -> open_holdout() -> record_evaluation_result()
        """
        if self._is_corrupted:
            raise HoldoutAuditIntegrityError(
                f"Cannot evaluate holdout: audit log at '{self.audit_storage_path}' is corrupted: {self._corruption_error}. "
                "Holdout dataset access is strictly locked."
            )
        raise HoldoutViolationError(
            "LEGACY_HOLDOUT_EVALUATION_DISABLED: Production holdout evaluation cannot retroactively "
            "preregister after observing metrics or auto-pass. Use create_preregistration() -> "
            "open_holdout() -> record_evaluation_result()."
        )

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
