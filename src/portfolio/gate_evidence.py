"""
Authoritative Gate Evidence Store & Artifact Registry (Pre-Paper Hardening 03C).

Invariants:
1. Gate evaluations must have authoritative storage and tamper-evident hashes.
2. Callers cannot fabricate valid gate bundles out of thin air: GateBundleArtifact
   must be minted from verified, persisted GateEvidenceRecord entries in the store.
3. Every gate evaluation record is immutable and append-only.
4. Any corruption in stored evaluations or bundles locks gate governance fail-closed (GOVERNANCE_LOCKED).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator

from src.portfolio.gates import (
    StrategyGateResult,
    GateStatus,
    CANONICAL_GATE_TYPES,
    FORBIDDEN_PASS_FINGERPRINTS,
    validate_gate_bundle,
)


class GateEvidenceError(Exception):
    """Base exception for gate evidence storage and integrity errors."""
    pass


class GateEvidenceViolationError(GateEvidenceError):
    """Raised when gate evidence provenance, duplicate ID, or invalid bundle occurs."""
    pass


class GateEvidenceIntegrityError(GateEvidenceError):
    """Raised when gate evidence persistence is corrupted, tampered with, or unverified."""
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
    "",
}


def _compute_record_hash(
    gate_evidence_id: str,
    strategy_id: str,
    strategy_version: str,
    gate_type: str,
    dataset_fingerprint: str,
    config_fingerprint: str,
    parameter_set_fingerprint: str,
    git_sha: str,
    status_str: str,
    score: float,
) -> str:
    raw = (
        f"{gate_evidence_id}:{strategy_id}:{strategy_version}:{gate_type}:"
        f"{dataset_fingerprint}:{config_fingerprint}:{parameter_set_fingerprint}:"
        f"{git_sha}:{status_str}:{score:.8f}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _compute_bundle_hash(
    gate_bundle_id: str,
    strategy_id: str,
    strategy_version: str,
    dataset_fingerprint: str,
    config_fingerprint: str,
    parameter_set_fingerprint: str,
    git_sha: str,
    evidence_ids: Dict[str, str],
) -> str:
    ev_json = json.dumps(dict(sorted(evidence_ids.items())), sort_keys=True)
    raw = (
        f"{gate_bundle_id}:{strategy_id}:{strategy_version}:{dataset_fingerprint}:"
        f"{config_fingerprint}:{parameter_set_fingerprint}:{git_sha}:{ev_json}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class GateEvidenceRecord(BaseModel):
    """Immutable, tamper-evident record of a single portfolio gate evaluation."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_evidence_id: str
    strategy_id: str
    strategy_version: str
    gate_type: str
    dataset_fingerprint: str
    config_fingerprint: str
    parameter_set_fingerprint: str
    git_sha: str
    gate_result: StrategyGateResult
    experiment_ids: List[str] = Field(default_factory=list)
    created_at_utc: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    record_hash: str = ""

    @model_validator(mode="before")
    @classmethod
    def _validate_and_hash(cls, data: Any) -> Any:
        if isinstance(data, dict):
            required = (
                "gate_evidence_id",
                "strategy_id",
                "strategy_version",
                "gate_type",
                "dataset_fingerprint",
                "config_fingerprint",
                "parameter_set_fingerprint",
                "git_sha",
            )
            for f in required:
                v = str(data.get(f, "")).strip()
                if not v:
                    raise ValueError(f"GateEvidenceRecord '{f}' must be a non-empty string.")
                if v.lower() in FORBIDDEN_PROVENANCE_PLACEHOLDERS:
                    raise ValueError(f"GateEvidenceRecord '{f}' contains prohibited placeholder '{v}'.")

            gr = data.get("gate_result")
            if not gr:
                raise ValueError("GateEvidenceRecord 'gate_result' must be provided.")
            if isinstance(gr, dict):
                gr_obj = StrategyGateResult(**gr)
                data["gate_result"] = gr_obj
            elif isinstance(gr, StrategyGateResult):
                gr_obj = gr
            else:
                raise TypeError(f"gate_result must be StrategyGateResult or dict, got {type(gr).__name__}")

            computed = _compute_record_hash(
                gate_evidence_id=str(data["gate_evidence_id"]),
                strategy_id=str(data["strategy_id"]),
                strategy_version=str(data["strategy_version"]),
                gate_type=str(data["gate_type"]),
                dataset_fingerprint=str(data["dataset_fingerprint"]),
                config_fingerprint=str(data["config_fingerprint"]),
                parameter_set_fingerprint=str(data["parameter_set_fingerprint"]),
                git_sha=str(data["git_sha"]),
                status_str=gr_obj.status.value,
                score=gr_obj.score,
            )
            provided = data.get("record_hash")
            if provided and provided != computed:
                raise ValueError(
                    f"GateEvidenceRecord record_hash mismatch: provided '{provided}' != computed '{computed}'"
                )
            data["record_hash"] = computed
        return data


class GateBundleArtifact(BaseModel):
    """Immutable, verified bundle binding canonical Gates A-D from authoritative store."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_bundle_id: str
    strategy_id: str
    strategy_version: str
    dataset_fingerprint: str
    config_fingerprint: str
    parameter_set_fingerprint: str
    git_sha: str
    gate_evidence_ids: Dict[str, str]  # Must contain canonical keys "A", "B", "C", "D"
    status: str = "VERIFIED"
    created_at_utc: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    bundle_hash: str = ""

    @model_validator(mode="before")
    @classmethod
    def _validate_and_hash(cls, data: Any) -> Any:
        if isinstance(data, dict):
            required = (
                "gate_bundle_id",
                "strategy_id",
                "strategy_version",
                "dataset_fingerprint",
                "config_fingerprint",
                "parameter_set_fingerprint",
                "git_sha",
            )
            for f in required:
                v = str(data.get(f, "")).strip()
                if not v:
                    raise ValueError(f"GateBundleArtifact '{f}' must be a non-empty string.")
                if v.lower() in FORBIDDEN_PROVENANCE_PLACEHOLDERS:
                    raise ValueError(f"GateBundleArtifact '{f}' contains prohibited placeholder '{v}'.")

            ev_ids = data.get("gate_evidence_ids")
            if not isinstance(ev_ids, dict):
                raise ValueError("GateBundleArtifact 'gate_evidence_ids' must be a dictionary.")
            for letter in ("A", "B", "C", "D"):
                if letter not in ev_ids or not str(ev_ids[letter]).strip():
                    raise ValueError(f"GateBundleArtifact missing canonical Gate {letter} in gate_evidence_ids.")

            computed = _compute_bundle_hash(
                gate_bundle_id=str(data["gate_bundle_id"]),
                strategy_id=str(data["strategy_id"]),
                strategy_version=str(data["strategy_version"]),
                dataset_fingerprint=str(data["dataset_fingerprint"]),
                config_fingerprint=str(data["config_fingerprint"]),
                parameter_set_fingerprint=str(data["parameter_set_fingerprint"]),
                git_sha=str(data["git_sha"]),
                evidence_ids=ev_ids,
            )
            provided = data.get("bundle_hash")
            if provided and provided != computed:
                raise ValueError(
                    f"GateBundleArtifact bundle_hash mismatch: provided '{provided}' != computed '{computed}'"
                )
            data["bundle_hash"] = computed
        return data


class GateEvaluationStore:
    """
    Authoritative, append-only store for gate evaluations and verified gate bundles.
    Enforces provenance matching, duplicate detection, and tamper-evident hashes.
    Any corruption triggers fail-closed locking (GOVERNANCE_LOCKED).
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        raise_on_corruption: bool = True,
    ):
        self.storage_dir = Path(storage_dir or "data/portfolio")
        self.evaluations_path = self.storage_dir / "gate_evaluations.json"
        self.bundles_path = self.storage_dir / "gate_bundles.json"
        self.raise_on_corruption = raise_on_corruption

        self._evaluations: Dict[str, GateEvidenceRecord] = {}
        self._bundles: Dict[str, GateBundleArtifact] = {}
        self._is_corrupted: bool = False
        self._corruption_error: Optional[str] = None

        self._load_storage()

    @property
    def is_corrupted(self) -> bool:
        return self._is_corrupted

    def _persist_atomic(self, path: Path, data: List[Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f".tmp_{path.name}_{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)

    def _load_storage(self) -> None:
        """Load and verify hashes for all evaluations and bundles."""
        if self.evaluations_path.exists():
            try:
                with open(self.evaluations_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError(f"Evaluations file must be a JSON list, got {type(data).__name__}")
                for item in data:
                    rec = GateEvidenceRecord(**item)
                    if rec.gate_evidence_id in self._evaluations:
                        raise ValueError(f"Duplicate gate_evidence_id '{rec.gate_evidence_id}' in storage.")
                    self._evaluations[rec.gate_evidence_id] = rec
            except Exception as e:
                self._is_corrupted = True
                self._corruption_error = f"Gate evaluations storage corrupted: {e}"
                if self.raise_on_corruption:
                    raise GateEvidenceIntegrityError(f"Gate evaluations storage corrupted: {e}") from e
                return

        if self.bundles_path.exists():
            try:
                with open(self.bundles_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError(f"Bundles file must be a JSON list, got {type(data).__name__}")
                for item in data:
                    bundle = GateBundleArtifact(**item)
                    if bundle.gate_bundle_id in self._bundles:
                        raise ValueError(f"Duplicate gate_bundle_id '{bundle.gate_bundle_id}' in storage.")
                    self._bundles[bundle.gate_bundle_id] = bundle
            except Exception as e:
                self._is_corrupted = True
                self._corruption_error = f"Gate bundles storage corrupted: {e}"
                if self.raise_on_corruption:
                    raise GateEvidenceIntegrityError(f"Gate bundles storage corrupted: {e}") from e
                return

    def record_gate_evaluation(
        self,
        strategy_id: str,
        strategy_version: str,
        gate_type: str,
        dataset_fingerprint: str,
        config_fingerprint: str,
        parameter_set_fingerprint: str,
        git_sha: str,
        gate_result: StrategyGateResult,
        experiment_ids: Optional[List[str]] = None,
        gate_evidence_id: Optional[str] = None,
    ) -> GateEvidenceRecord:
        """Record an immutable gate evaluation in the authoritative store."""
        if self._is_corrupted:
            raise GateEvidenceIntegrityError(
                f"Cannot record gate evaluation: store is corrupted (GOVERNANCE_LOCKED): {self._corruption_error}."
            )

        # Validate gate_result provenance against caller provenance
        if (
            gate_result.strategy_id != strategy_id
            or gate_result.strategy_version != strategy_version
            or gate_result.dataset_fingerprint != dataset_fingerprint
            or gate_result.config_fingerprint != config_fingerprint
        ):
            raise GateEvidenceViolationError(
                "Provenance mismatch between StrategyGateResult and record parameters: "
                f"result=({gate_result.strategy_id}, {gate_result.strategy_version}, {gate_result.dataset_fingerprint}) "
                f"!= params=({strategy_id}, {strategy_version}, {dataset_fingerprint})"
            )

        now_ns = time.time_ns()
        ev_id = gate_evidence_id or f"gate_ev_{strategy_id}_{strategy_version}_{gate_type}_{now_ns}"
        if ev_id in self._evaluations:
            raise GateEvidenceViolationError(f"Gate evidence ID '{ev_id}' already exists in store.")

        record = GateEvidenceRecord(
            gate_evidence_id=ev_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            dataset_fingerprint=dataset_fingerprint,
            config_fingerprint=config_fingerprint,
            parameter_set_fingerprint=parameter_set_fingerprint,
            git_sha=git_sha,
            gate_result=gate_result,
            experiment_ids=experiment_ids or list(gate_result.experiment_ids),
            created_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        self._evaluations[ev_id] = record
        self._persist_atomic(
            self.evaluations_path,
            [r.model_dump() for r in self._evaluations.values()],
        )
        return record

    def create_gate_bundle(
        self,
        strategy_id: str,
        strategy_version: str,
        dataset_fingerprint: str,
        config_fingerprint: str,
        parameter_set_fingerprint: str,
        git_sha: str,
        gate_evidence_ids: Dict[str, str],
        gate_bundle_id: Optional[str] = None,
    ) -> GateBundleArtifact:
        """
        Create a VERIFIED GateBundleArtifact by fetching and validating 4 gate evaluations.
        Enforces that all 4 gates exist in store, match provenance, and pass validate_gate_bundle().
        """
        if self._is_corrupted:
            raise GateEvidenceIntegrityError(
                f"Cannot create gate bundle: store is corrupted (GOVERNANCE_LOCKED): {self._corruption_error}."
            )

        now_ns = time.time_ns()
        bundle_id = gate_bundle_id or f"bundle_{strategy_id}_{strategy_version}_{now_ns}"
        if bundle_id in self._bundles:
            raise GateEvidenceViolationError(f"Gate bundle ID '{bundle_id}' already exists in store.")

        # Check required canonical keys
        for letter in ("A", "B", "C", "D"):
            if letter not in gate_evidence_ids:
                raise GateEvidenceViolationError(
                    f"Cannot create gate bundle: missing canonical Gate {letter} in gate_evidence_ids."
                )

        # Fetch records and check provenance
        records_to_validate: List[StrategyGateResult] = []
        for letter in ("A", "B", "C", "D"):
            ev_id = gate_evidence_ids[letter]
            rec = self._evaluations.get(ev_id)
            if not rec:
                raise GateEvidenceViolationError(
                    f"Gate evidence record '{ev_id}' for Gate {letter} does not exist in store."
                )
            if (
                rec.strategy_id != strategy_id
                or rec.strategy_version != strategy_version
                or rec.dataset_fingerprint != dataset_fingerprint
                or rec.config_fingerprint != config_fingerprint
                or rec.parameter_set_fingerprint != parameter_set_fingerprint
                or rec.git_sha != git_sha
            ):
                raise GateEvidenceViolationError(
                    f"Provenance mismatch for Gate {letter} record '{ev_id}' against bundle parameters: "
                    f"rec=({rec.strategy_id}, {rec.dataset_fingerprint}, {rec.git_sha}) "
                    f"!= bundle=({strategy_id}, {dataset_fingerprint}, {git_sha})"
                )
            records_to_validate.append(rec.gate_result)

        # Run strict validation
        is_valid, reasons = validate_gate_bundle(records_to_validate)
        if not is_valid:
            raise GateEvidenceViolationError(
                f"Cannot create VERIFIED gate bundle: gate evaluations failed validation: {reasons}"
            )

        artifact = GateBundleArtifact(
            gate_bundle_id=bundle_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            dataset_fingerprint=dataset_fingerprint,
            config_fingerprint=config_fingerprint,
            parameter_set_fingerprint=parameter_set_fingerprint,
            git_sha=git_sha,
            gate_evidence_ids=gate_evidence_ids,
            status="VERIFIED",
            created_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        self._bundles[bundle_id] = artifact
        self._persist_atomic(
            self.bundles_path,
            [b.model_dump() for b in self._bundles.values()],
        )
        return artifact

    def record_and_bundle_gates(
        self,
        gate_results: Union[Dict[str, StrategyGateResult], List[StrategyGateResult]],
        parameter_set_fingerprint: str,
        git_sha: str,
        experiment_ids: Optional[List[str]] = None,
        gate_bundle_id: Optional[str] = None,
    ) -> Tuple[GateBundleArtifact, Dict[str, GateEvidenceRecord]]:
        """
        Record all 4 gate results in the store and create a verified GateBundleArtifact.
        Ensures atomic end-to-end bundling of portfolio gates.
        """
        # 1. Pre-validate bundle structure and pass status
        is_valid, reasons = validate_gate_bundle(gate_results)
        if not is_valid:
            raise GateEvidenceViolationError(
                f"Cannot record and bundle gates: validation failed: {reasons}"
            )

        # Map to canonical letters
        gate_by_letter: Dict[str, StrategyGateResult] = {}
        gates_list = list(gate_results.values()) if isinstance(gate_results, dict) else list(gate_results)
        for r in gates_list:
            found = None
            gt = (r.gate_type or "").upper()
            for letter, canon in CANONICAL_GATE_TYPES.items():
                if canon in gt or letter == r.gate_name:
                    found = letter
                    break
            if not found and r.gate_name and r.gate_name.upper().startswith("GATE "):
                cand = r.gate_name.split()[1][:1].upper()
                if cand in CANONICAL_GATE_TYPES:
                    found = cand
            if not found:
                raise GateEvidenceViolationError(f"Unrecognized gate type in results: {r.gate_type}")
            gate_by_letter[found] = r

        first_gate = gate_by_letter["A"]
        strategy_id = first_gate.strategy_id
        strategy_version = first_gate.strategy_version
        dataset_fingerprint = first_gate.dataset_fingerprint
        config_fingerprint = first_gate.config_fingerprint

        # 2. Record each gate evaluation
        recorded_records: Dict[str, GateEvidenceRecord] = {}
        evidence_ids: Dict[str, str] = {}
        for letter in ("A", "B", "C", "D"):
            gr = gate_by_letter[letter]
            rec = self.record_gate_evaluation(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gr.gate_type,
                dataset_fingerprint=dataset_fingerprint,
                config_fingerprint=config_fingerprint,
                parameter_set_fingerprint=parameter_set_fingerprint,
                git_sha=git_sha,
                gate_result=gr,
                experiment_ids=experiment_ids or list(gr.experiment_ids),
            )
            recorded_records[letter] = rec
            evidence_ids[letter] = rec.gate_evidence_id

        # 3. Create verified bundle artifact
        bundle_art = self.create_gate_bundle(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            dataset_fingerprint=dataset_fingerprint,
            config_fingerprint=config_fingerprint,
            parameter_set_fingerprint=parameter_set_fingerprint,
            git_sha=git_sha,
            gate_evidence_ids=evidence_ids,
            gate_bundle_id=gate_bundle_id,
        )

        return bundle_art, recorded_records

    def get_gate_bundle(self, gate_bundle_id: str) -> Optional[GateBundleArtifact]:
        if self._is_corrupted:
            raise GateEvidenceIntegrityError(f"Store corrupted: {self._corruption_error}")
        return self._bundles.get(gate_bundle_id)

    def get_gate_evaluation(self, gate_evidence_id: str) -> Optional[GateEvidenceRecord]:
        if self._is_corrupted:
            raise GateEvidenceIntegrityError(f"Store corrupted: {self._corruption_error}")
        return self._evaluations.get(gate_evidence_id)

    def list_bundles_for_strategy(self, strategy_id: str) -> List[GateBundleArtifact]:
        if self._is_corrupted:
            raise GateEvidenceIntegrityError(f"Store corrupted: {self._corruption_error}")
        return [b for b in self._bundles.values() if b.strategy_id == strategy_id]

    def list_evaluations_for_strategy(self, strategy_id: str) -> List[GateEvidenceRecord]:
        if self._is_corrupted:
            raise GateEvidenceIntegrityError(f"Store corrupted: {self._corruption_error}")
        return [e for e in self._evaluations.values() if e.strategy_id == strategy_id]
