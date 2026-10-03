"""Outbox replay: local-first records -> remote backend with bounded exponential backoff."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from .backend import (
    BackendUnavailableError,
    ImmutableConflictError,
    LocalPersistenceBackend,
    NotConfiguredError,
    PersistenceBackend,
)


def backoff_delay(attempts: int, base: float = 1.0, cap: float = 300.0) -> float:
    return min(cap, base * (2 ** max(0, attempts)))


@dataclass
class SyncReport:
    synced: int = 0
    retried: int = 0
    failed: int = 0
    not_configured: bool = False
    errors: List[str] = field(default_factory=list)


class OutboxSyncer:
    """Replays PENDING outbox rows. Safe to run repeatedly: remote writes are idempotent."""

    def __init__(
        self,
        local: LocalPersistenceBackend,
        remote: PersistenceBackend,
        max_attempts: int = 8,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        batch_size: int = 100,
    ):
        self.local = local
        self.remote = remote
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.batch_size = batch_size

    def sync_once(self) -> SyncReport:
        report = SyncReport()
        for entry in self.local.outbox_due(self.batch_size):
            data = self.local.get(entry["table_name"], entry["key"])
            if data is None:  # cannot happen (no deletes); fail closed rather than skip silently
                self.local.outbox_mark_retry(entry["outbox_id"], "local record missing", 0.0, failed=True)
                report.failed += 1
                continue
            try:
                self.remote.put(entry["table_name"], entry["key"], data)
                self.local.outbox_mark_synced(entry["outbox_id"])
                report.synced += 1
            except NotConfiguredError:
                report.not_configured = True  # leave PENDING, do not burn attempts
                break
            except ImmutableConflictError as e:
                self.local.outbox_mark_retry(entry["outbox_id"], f"IMMUTABLE_CONFLICT: {e}", 0.0, failed=True)
                report.failed += 1
                report.errors.append(str(e))
            except (BackendUnavailableError, Exception) as e:  # noqa: BLE001 - any remote failure is retryable
                attempts = entry["attempts"] + 1
                failed = attempts >= self.max_attempts
                delay = backoff_delay(entry["attempts"], self.base_delay, self.max_delay)
                self.local.outbox_mark_retry(entry["outbox_id"], str(e), self.local._clock() + delay, failed=failed)
                report.failed += 1 if failed else 0
                report.retried += 0 if failed else 1
                report.errors.append(str(e))
        return report
