"""Small local-only process health registry; it stores no credentials or market data."""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ("supervisor", "markets_recorder", "paper_runtime", "pumpfun_recorder", "pumpfun_paper", "leader_paper", "x_watcher")
STATUSES = {"NEVER_STARTED", "STARTING", "RUNNING", "DEGRADED", "ERROR", "DISABLED", "STOPPED"}
_SECRET = re.compile(r"(?i)(api[_-]?key|authorization|secret|token)(\s*[:=]\s*|\s+)([^\s,;]+)")
_BEARER = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+")
_URL_QUERY = re.compile(r"(https?://[^\s?]+)\?[^\s]+", re.I)


def _iso(ts: Optional[float] = None) -> Optional[str]:
    return datetime.fromtimestamp(ts if ts is not None else time.time(), tz=timezone.utc).isoformat()


def sanitize_error(message: Any) -> str:
    """Keep actionable exception context while removing credentials and URL query strings."""
    value = str(message or "")[:500]
    value = _BEARER.sub(r"\1[REDACTED]", value)
    value = _SECRET.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", value)
    return _URL_QUERY.sub(r"\1?[REDACTED]", value)


class RuntimeHealth:
    def __init__(self, component: str, root: Path = ROOT):
        if component not in COMPONENTS:
            raise ValueError(f"Unknown runtime component: {component}")
        self.component = component
        self.path = Path(root) / "data" / "runtime" / "health" / f"{component}.json"

    def update(self, status: str, *, enabled: bool = True, started: bool = False,
               success: bool = False, error: Optional[BaseException] = None,
               pid: Optional[int] = None, **extra: Any) -> Dict[str, Any]:
        if status not in STATUSES:
            raise ValueError(f"Invalid runtime status: {status}")
        prev = self.read()
        row = {"component": self.component, "status": status, "enabled": bool(enabled),
               "started_at": _iso() if started else prev.get("started_at"),
               "last_heartbeat": _iso(),
               "last_success": _iso() if success else prev.get("last_success"),
               "last_error_type": type(error).__name__ if error else prev.get("last_error_type"),
               "last_error_message_sanitized": sanitize_error(error) if error else prev.get("last_error_message_sanitized"),
               "pid": (int(pid) if pid is not None else None) if status in ("NEVER_STARTED", "DISABLED", "STOPPED", "ERROR")
                     else int(pid if pid is not None else os.getpid())}
        row.update(extra)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(row, sort_keys=True), encoding="utf-8")
        temp.replace(self.path)
        return row

    def read(self) -> Dict[str, Any]:
        try:
            row = json.loads(self.path.read_text(encoding="utf-8"))
            return row if isinstance(row, dict) else {}
        except (OSError, ValueError):
            return {}


def runtime_health_snapshot(root: Path = ROOT, stale_after_s: int = 120) -> Dict[str, Any]:
    root = Path(root)
    cfg_path = root / "config" / "pumpfun.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    except (OSError, ValueError):
        cfg = {}
    enabled = {name: True for name in COMPONENTS}
    enabled["pumpfun_recorder"] = bool(cfg.get("enabled", True))
    enabled["pumpfun_paper"] = bool(cfg.get("enabled", True) and cfg.get("paper_enabled", True))
    enabled["x_watcher"] = bool(cfg.get("enabled", True) and cfg.get("x_enabled", True))
    x_has_key = False
    if enabled["x_watcher"]:
        try:
            from src.common.secret_loader import get_secret
            x_has_key = bool(get_secret("XAI_API_KEY", root))
        except Exception:
            x_has_key = False
    out: Dict[str, Any] = {}
    now = time.time()
    for name in COMPONENTS:
        row = RuntimeHealth(name, root).read()
        row = {"component": name, "status": "NEVER_STARTED", "enabled": enabled[name],
               "started_at": None, "last_heartbeat": None, "last_success": None,
               "last_error_type": None, "last_error_message_sanitized": None, **row}
        row["enabled"] = enabled[name]
        if not enabled[name]:
            row["status"] = "DISABLED"
            row["pid"] = None
        elif name == "x_watcher" and not x_has_key:
            row["status"] = "DISABLED"
            row["disabled_reason"] = "NO_KEY"
            row["pid"] = None
        elif row.get("status") in ("STARTING", "RUNNING", "DEGRADED"):
            pid = row.get("pid")
            alive = False
            if pid:
                try:
                    os.kill(int(pid), 0)
                    alive = True
                except (OSError, ValueError, TypeError):
                    pass
            if not alive:
                row["status"] = "STOPPED"
            else:
                try:
                    age = now - datetime.fromisoformat(row["last_heartbeat"]).timestamp()
                except (KeyError, TypeError, ValueError):
                    age = stale_after_s + 1
                if age > stale_after_s:
                    row["status"] = "DEGRADED"
        out[name] = row
    return {"components": out, "generated_at": _iso(), "read_only": True}
