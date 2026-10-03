"""Credential handling and secret redaction.

Quant OS never requires WITHDRAW permission. READ allowed when needed; TRADE only when the live phase
begins; WITHDRAW is NEVER required (keep withdrawals disabled; IP-whitelist when a fixed-IP host exists).
Secrets are held only in memory in ``Secret`` objects: never persisted, never serialized, never logged.
"""
from __future__ import annotations

import os
import re
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

NOT_CONFIGURED = "NOT_CONFIGURED"
CONFIGURED = "CONFIGURED"

# venue -> environment -> (id_var, secret_var)
VENUE_ENV: Dict[str, Dict[str, Tuple[str, str]]] = {
    "binance_perp": {"LIVE": ("BINANCE_API_KEY", "BINANCE_API_SECRET"),
                     "SANDBOX": ("BINANCE_TESTNET_API_KEY", "BINANCE_TESTNET_API_SECRET")},
    "bybit": {"LIVE": ("BYBIT_API_KEY", "BYBIT_API_SECRET"),
              "SANDBOX": ("BYBIT_TESTNET_API_KEY", "BYBIT_TESTNET_API_SECRET")},
    "deribit": {"LIVE": ("DERIBIT_CLIENT_ID", "DERIBIT_CLIENT_SECRET"),
                "SANDBOX": ("DERIBIT_TESTNET_CLIENT_ID", "DERIBIT_TESTNET_CLIENT_SECRET")},
}


class Secret:
    """Opaque secret. repr/str never reveal the value; value is not picklable into logs by accident."""
    __slots__ = ("_v",)

    def __init__(self, value: str):
        object.__setattr__(self, "_v", value)

    def reveal(self) -> str:
        return self._v

    def __repr__(self) -> str:
        return "Secret(***)"

    __str__ = __repr__

    def __reduce__(self):  # pragma: no cover
        raise TypeError("Secret cannot be serialized")

    def __setattr__(self, k, v):  # pragma: no cover
        raise AttributeError("immutable")


class CredentialsNotConfigured(Exception):
    pass


class CredentialProvider:
    def __init__(self, env: Optional[Mapping[str, str]] = None):
        self._env = env if env is not None else os.environ

    def _vars(self, venue: str, environment: str) -> Tuple[str, str]:
        try:
            return VENUE_ENV[venue][environment]
        except KeyError:
            raise CredentialsNotConfigured(f"unknown venue/environment {venue}/{environment}")

    def status(self, venue: str, environment: str = "LIVE") -> Dict[str, object]:
        """Status only. Never returns values, lengths or fingerprints of secrets."""
        try:
            a, b = self._vars(venue, environment)
        except CredentialsNotConfigured:
            return {"venue": venue, "environment": environment, "status": NOT_CONFIGURED, "missing": []}
        missing = [n for n in (a, b) if not (self._env.get(n) or "").strip()]
        return {"venue": venue, "environment": environment,
                "status": NOT_CONFIGURED if missing else CONFIGURED, "missing": missing,
                "permissions_policy": "READ allowed; TRADE only in live phase; WITHDRAW never required"}

    def is_configured(self, venue: str, environment: str = "LIVE") -> bool:
        return self.status(venue, environment)["status"] == CONFIGURED

    def get(self, venue: str, environment: str = "LIVE") -> Tuple[Secret, Secret]:
        a, b = self._vars(venue, environment)
        va, vb = (self._env.get(a) or "").strip(), (self._env.get(b) or "").strip()
        if not va or not vb:
            raise CredentialsNotConfigured(f"{venue}/{environment} credentials not configured")
        return Secret(va), Secret(vb)

    def known_values(self) -> List[str]:
        vals = []
        for envs in VENUE_ENV.values():
            for pair in envs.values():
                for n in pair:
                    v = (self._env.get(n) or "").strip()
                    if v:
                        vals.append(v)
        return vals


_SENSITIVE_KEY = re.compile(r"(secret|api[_-]?key|token|signature|passw|authorization|client[_-]?id|sign)", re.I)


def redact_text(text: str, secrets: Iterable[str] = ()) -> str:
    out = str(text)
    for s in secrets:
        if s and len(s) >= 4:
            out = out.replace(s, "***")
    out = re.sub(r"(signature=)[0-9a-fA-F]+", r"\1***", out)
    out = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+", r"\1***", out)
    return out


def scrub(obj, secrets: Iterable[str] = ()):
    """Recursively redact sensitive keys and any known secret values from a payload."""
    secrets = list(secrets)
    if isinstance(obj, dict):
        return {k: ("***" if _SENSITIVE_KEY.search(str(k)) else scrub(v, secrets)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [scrub(v, secrets) for v in obj]
    if isinstance(obj, Secret):
        return "***"
    if isinstance(obj, str):
        return redact_text(obj, secrets)
    return obj
