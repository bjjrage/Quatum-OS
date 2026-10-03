"""Environment-driven Supabase configuration. Never fabricates credentials."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class SupabaseConfig:
    url: Optional[str] = None
    service_role_key: Optional[str] = None
    anon_key: Optional[str] = None
    bucket_market_data: Optional[str] = None
    bucket_research: Optional[str] = None

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "SupabaseConfig":
        e = os.environ if env is None else env

        def g(name: str) -> Optional[str]:
            v = (e.get(name) or "").strip()
            return v or None

        return cls(
            url=g("SUPABASE_URL"),
            service_role_key=g("SUPABASE_SERVICE_ROLE_KEY"),
            anon_key=g("SUPABASE_ANON_KEY"),
            bucket_market_data=g("SUPABASE_STORAGE_BUCKET_MARKET_DATA"),
            bucket_research=g("SUPABASE_STORAGE_BUCKET_RESEARCH"),
        )

    def missing(self) -> list:
        miss = []
        if not self.url:
            miss.append("SUPABASE_URL")
        if not self.service_role_key:
            miss.append("SUPABASE_SERVICE_ROLE_KEY")
        return miss

    @property
    def is_configured(self) -> bool:
        return not self.missing()

    def status(self) -> Dict[str, Any]:
        """Safe status (never includes key material)."""
        if self.is_configured:
            return {
                "status": "CONFIGURED_UNVERIFIED",
                "source": "SUPABASE",
                "reason": "Credentials present; connectivity not verified by this call.",
                "buckets": {
                    "market_data": bool(self.bucket_market_data),
                    "research": bool(self.bucket_research),
                },
            }
        return {
            "status": "NOT_CONFIGURED",
            "source": "SUPABASE",
            "reason": f"{', '.join(self.missing())} not configured",
        }

    def __repr__(self) -> str:  # never leak secrets in logs/tracebacks
        return (
            f"SupabaseConfig(url={self.url!r}, service_role_key={'***' if self.service_role_key else None}, "
            f"anon_key={'***' if self.anon_key else None})"
        )
