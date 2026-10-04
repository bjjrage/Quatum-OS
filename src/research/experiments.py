"""
Experiment Registry and Multiple Testing Accounting Framework.

Core Invariants:
1. Every candidate model, feature, and parameter variant generates an auditable record.
2. The system itself counts trials (trial_count). Researcher cannot hide failed trials.
3. Deletion or overwrite of experiments is strictly forbidden.
4. Experiment search path remains fully visible for multiple testing corrections (DSR, FDR).
5. Registry persists to durable append-only storage and recomputes trial count across process restarts.
"""

from __future__ import annotations

from enum import Enum
import json
import os
from pathlib import Path
import time
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field, ConfigDict, model_validator


class RegistryIntegrityStatus(str, Enum):
    HEALTHY = "HEALTHY"
    CORRUPTED = "CORRUPTED"
    MANUAL_REPAIR_REQUIRED = "MANUAL_REPAIR_REQUIRED"


class ExperimentRegistryIntegrityError(RuntimeError):
    """Raised when experiment registry storage is corrupted, partial, or unverified."""
    pass


class ExperimentRecord(BaseModel):
    """Auditable record of a single empirical strategy evaluation (23 fields)."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: str
    strategy_id: str
    strategy_version: str = "1.0.0"
    git_sha: str = "UNKNOWN"
    dataset_fingerprint: str = ""
    config_fingerprint: str = ""
    feature_definition_hash: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    entry_model: str = "DEFAULT"
    exit_model: str = "DEFAULT"
    factor_model: str = "NONE"
    regime_definition: str = "GLOBAL"
    universe_definition: str = "DEFAULT"
    cost_model_version: str = "v1"
    research_period: str = ""
    validation_period: str = ""
    holdout_period: str = ""
    random_seed: int = 42
    result_metrics: Dict[str, Any] = Field(default_factory=dict)
    gate_result: str = "PENDING"  # PASS, FAIL, PENDING
    raw_p_value: Optional[float] = None
    created_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    falsification_evidence: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _validate_raw_p_value(cls, data: Any) -> Any:
        if isinstance(data, dict):
            p = data.get("raw_p_value")
            if p is not None:
                if not isinstance(p, (int, float)) or isinstance(p, bool):
                    raise ValueError(f"raw_p_value must be float, got {type(p).__name__}")
                import math
                if math.isnan(p) or math.isinf(p) or not (0.0 <= float(p) <= 1.0):
                    raise ValueError(f"raw_p_value must be finite float in [0.0, 1.0], got {p}")
        return data


class MultipleTestingContext(BaseModel):
    """Immutable context for multiple testing corrections across a strategy's search path."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str
    trial_count: int = Field(ge=0)
    experiment_ids: List[str] = Field(default_factory=list)
    registry_integrity_status: RegistryIntegrityStatus = RegistryIntegrityStatus.HEALTHY
    raw_p_values: List[float] = Field(default_factory=list)
    candidate_raw_p_value: Optional[float] = None
    # Per-period (NOT annualized) Sharpe of every recorded trial; DSR needs their cross-trial variance
    trial_sharpes: List[float] = Field(default_factory=list)

    @property
    def trial_sharpe_variance(self) -> Optional[float]:
        """Sample variance of per-period Sharpes across trials (None when fewer than 2 are recorded)."""
        import math
        vals = [float(x) for x in self.trial_sharpes if isinstance(x, (int, float)) and math.isfinite(x)]
        if len(vals) < 2:
            return None
        m = sum(vals) / len(vals)
        var = sum((v - m) ** 2 for v in vals) / (len(vals) - 1)
        return var if var > 0.0 else None

    @property
    def is_complete(self) -> bool:
        """Whether raw p-values are available for all recorded trials and candidate."""
        return len(self.raw_p_values) >= self.trial_count and self.candidate_raw_p_value is not None


class ExperimentRegistry:
    """
    Central repository for all research experiments.
    Enforces durable append-only storage and automatic multiple-testing accounting.
    Fail-closed: Any corrupted record locks the registry and prevents undercounting trials.
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = Path(storage_dir or "data/experiments")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._experiments: Dict[str, ExperimentRecord] = {}
        self._strategy_trial_counts: Dict[str, int] = {}
        self.status: RegistryIntegrityStatus = RegistryIntegrityStatus.HEALTHY
        self.quarantine_log: List[Dict[str, Any]] = []
        self._load_from_storage()

    def _load_from_storage(self) -> None:
        """Scan storage directory, load all persisted experiment records, and compute trial counts."""
        corrupted_files: List[Tuple[str, str]] = []
        for json_file in sorted(self.storage_dir.glob("*.json")):
            if json_file.name.startswith(".tmp_") or json_file.name == "quarantine_integrity_log.json":
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                record = ExperimentRecord(**data)
                if record.experiment_id in self._experiments:
                    raise ValueError(f"Duplicate experiment_id '{record.experiment_id}' in storage")
                self._experiments[record.experiment_id] = record
                self._strategy_trial_counts[record.strategy_id] = (
                    self._strategy_trial_counts.get(record.strategy_id, 0) + 1
                )
            except Exception as e:
                self.status = RegistryIntegrityStatus.CORRUPTED
                err_detail = {
                    "file": str(json_file),
                    "error": str(e),
                    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                self.quarantine_log.append(err_detail)
                corrupted_files.append((str(json_file), str(e)))

        if corrupted_files:
            self.status = RegistryIntegrityStatus.MANUAL_REPAIR_REQUIRED
            # Persist quarantine log for forensic investigation
            quarantine_path = self.storage_dir / "quarantine_integrity_log.json"
            try:
                with open(quarantine_path, "w", encoding="utf-8") as qf:
                    json.dump(self.quarantine_log, qf, indent=2)
            except Exception:
                pass
            raise ExperimentRegistryIntegrityError(
                f"ExperimentRegistry corruption detected: {len(corrupted_files)} files could not be cleanly loaded. "
                f"Status set to {self.status.value}. Manual repair required before research can proceed: {corrupted_files}"
            )

    def record_experiment(self, record: ExperimentRecord) -> int:
        """
        Record a new experiment.
        Persists to durable append-only storage.
        Automatically increments strategy trial count.
        Returns the updated total trial count for the strategy.
        """
        if self.status != RegistryIntegrityStatus.HEALTHY:
            raise ExperimentRegistryIntegrityError(
                f"Cannot record experiment: registry integrity status is {self.status.value}. "
                f"Fail-closed invariant prevents writing to corrupted registry."
            )

        if record.experiment_id in self._experiments:
            raise ValueError(f"Experiment ID '{record.experiment_id}' already exists. Modification is forbidden.")

        # Persist atomically to disk
        file_path = self.storage_dir / f"{record.experiment_id}.json"
        tmp_file = self.storage_dir / f".tmp_{record.experiment_id}_{os.getpid()}"
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(record.model_dump_json(indent=2))
        os.replace(tmp_file, file_path)

        self._experiments[record.experiment_id] = record
        current_count = self._strategy_trial_counts.get(record.strategy_id, 0) + 1
        self._strategy_trial_counts[record.strategy_id] = current_count
        return current_count

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentRecord]:
        if self.status != RegistryIntegrityStatus.HEALTHY:
            raise ExperimentRegistryIntegrityError(
                f"Cannot retrieve experiment: registry integrity status is {self.status.value}."
            )
        return self._experiments.get(experiment_id)

    def get_trial_count(self, strategy_id: str) -> int:
        """Return the true number of historical trials evaluated for this strategy."""
        if self.status != RegistryIntegrityStatus.HEALTHY:
            raise ExperimentRegistryIntegrityError(
                f"Cannot return trial count: registry integrity status is {self.status.value}. "
                f"Fail-closed invariant prevents returning unverified or partial trial counts."
            )
        return self._strategy_trial_counts.get(strategy_id, 0)

    def list_experiments_for_strategy(self, strategy_id: str) -> List[ExperimentRecord]:
        """List all experiments for a strategy, preserving search path including failures."""
        if self.status != RegistryIntegrityStatus.HEALTHY:
            raise ExperimentRegistryIntegrityError(
                f"Cannot list experiments: registry integrity status is {self.status.value}."
            )
        return [exp for exp in self._experiments.values() if exp.strategy_id == strategy_id]

    def get_multiple_testing_context(
        self,
        strategy_id: str,
        candidate_raw_p_value: Optional[float] = None,
    ) -> MultipleTestingContext:
        """
        Return the immutable MultipleTestingContext for a strategy,
        fail-closed if the registry status is not HEALTHY.
        """
        if self.status != RegistryIntegrityStatus.HEALTHY:
            return MultipleTestingContext(
                strategy_id=strategy_id,
                trial_count=0,
                experiment_ids=[],
                registry_integrity_status=self.status,
                raw_p_values=[],
                candidate_raw_p_value=candidate_raw_p_value,
            )

        experiments = [exp for exp in self._experiments.values() if exp.strategy_id == strategy_id]
        trial_count = len(experiments)
        exp_ids = [e.experiment_id for e in experiments]
        p_vals = [e.raw_p_value for e in experiments if e.raw_p_value is not None]
        import math as _m
        sharpes = [
            float(e.result_metrics["sharpe_per_period"]) for e in experiments
            if isinstance(e.result_metrics.get("sharpe_per_period"), (int, float))
            and _m.isfinite(e.result_metrics["sharpe_per_period"])
        ]

        return MultipleTestingContext(
            strategy_id=strategy_id,
            trial_count=trial_count,
            experiment_ids=exp_ids,
            registry_integrity_status=self.status,
            raw_p_values=p_vals,
            candidate_raw_p_value=candidate_raw_p_value,
            trial_sharpes=sharpes,
        )

    def delete_experiment(self, experiment_id: str) -> None:
        """Non-negotiable Invariant: Deletion of experiments is strictly forbidden."""
        raise RuntimeError(
            "Governance Invariant Violated: Experiments cannot be deleted to hide failed trials. "
            "All empirical exploration must remain permanently auditable."
        )
