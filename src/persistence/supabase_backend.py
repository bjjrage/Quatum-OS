"""Supabase (PostgREST + Storage) adapters behind injectable transports.

No SDK dependency: a minimal urllib transport is provided, and everything is testable with a
mocked transport. When credentials are absent every call raises ``NotConfiguredError`` and
``status()`` reports NOT_CONFIGURED -- a successful cloud connection is never fabricated.
The service-role key is server-side only and never appears in repr/status/logs.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

from .backend import (
    INSERTED,
    UNCHANGED,
    BackendUnavailableError,
    ImmutableConflictError,
    NotConfiguredError,
    PersistenceBackend,
    PersistenceError,
    canonical_json,
    payload_hash,
)
from .config import SupabaseConfig
from .schema import get_spec, remote_row


class RestTransport(Protocol):
    def request(
        self, method: str, path: str, params: Optional[Dict[str, str]] = None,
        json_body: Any = None, headers: Optional[Dict[str, str]] = None, raw_body: Optional[bytes] = None,
    ) -> Tuple[int, Any]:
        """Return (http_status, parsed_json_or_bytes). Raise BackendUnavailableError on network failure."""


class UrllibRestTransport:
    def __init__(self, config: SupabaseConfig, timeout: float = 20.0):
        self._cfg = config
        self._timeout = timeout

    def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
        if not self._cfg.is_configured:
            raise NotConfiguredError(", ".join(self._cfg.missing()) + " not configured")
        url = self._cfg.url.rstrip("/") + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        hdrs = {"apikey": self._cfg.service_role_key, "Authorization": f"Bearer {self._cfg.service_role_key}"}
        hdrs.update(headers or {})
        body = raw_body
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, data=body, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                return resp.status, (json.loads(raw) if raw and "json" in ctype else raw)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise BackendUnavailableError(f"network error: {type(e).__name__}") from e


class SupabasePersistenceBackend(PersistenceBackend):
    name = "SUPABASE"

    def __init__(self, config: Optional[SupabaseConfig] = None, transport: Optional[RestTransport] = None):
        self.config = config or SupabaseConfig.from_env()
        self._transport = transport
        if self._transport is None and self.config.is_configured:
            self._transport = UrllibRestTransport(self.config)

    def _require(self) -> RestTransport:
        if self._transport is None:
            raise NotConfiguredError(", ".join(self.config.missing()) + " not configured")
        return self._transport

    @staticmethod
    def _check(status: int, body: Any) -> None:
        if status >= 500 or status == 429:
            raise BackendUnavailableError(f"remote error {status}")
        if status >= 400:
            raise PersistenceError(f"remote rejected request: {status} {str(body)[:200]}")

    def get(self, table: str, key: str) -> Optional[Dict[str, Any]]:
        spec = get_spec(table)
        status, body = self._require().request(
            "GET", f"/rest/v1/{table}", params={spec.pk: f"eq.{key}", "select": "payload"}
        )
        self._check(status, body)
        return body[0]["payload"] if body else None

    def put(self, table: str, key: str, data: Dict[str, Any], expected_hash: Optional[str] = None) -> str:
        spec = get_spec(table)
        existing = self.get(table, key)
        if existing is not None:
            curr_hash = payload_hash(existing)
            if canonical_json(existing) == canonical_json(data):
                return UNCHANGED
            if spec.immutable:
                raise ImmutableConflictError(f"remote {table}[{key}] is append-only with a different payload")
            if expected_hash is not None and curr_hash != expected_hash:
                raise PersistenceError(
                    f"Lost update detected on {table}[{key}]: expected hash {expected_hash} but found {curr_hash}."
                )
        elif expected_hash is not None:
            raise PersistenceError(
                f"Lost update detected on {table}[{key}]: expected hash {expected_hash} but record does not exist."
            )
        prefer = "resolution=merge-duplicates" if not spec.immutable else "resolution=ignore-duplicates"
        status, body = self._require().request(
            "POST", f"/rest/v1/{table}", params={"on_conflict": spec.pk},
            json_body=remote_row(table, key, data), headers={"Prefer": prefer + ",return=minimal"},
        )
        self._check(status, body)
        return INSERTED if existing is None else "UPDATED"

    def list(self, table: str, limit: Optional[int] = None, page_size: int = 1000, **filters: Any) -> List[Dict[str, Any]]:
        spec = get_spec(table)
        results: List[Dict[str, Any]] = []
        offset = 0
        actual_page_size = min(page_size, limit) if limit is not None else page_size

        while True:
            params = {
                "select": "payload",
                "order": f"{spec.pk}.asc",
                "limit": str(actual_page_size),
                "offset": str(offset),
            }
            for k, v in filters.items():
                params[k] = f"eq.{v}"

            headers = {
                "Range-Unit": "items",
                "Range": f"{offset}-{offset + actual_page_size - 1}",
            }
            status, body = self._require().request("GET", f"/rest/v1/{table}", params=params, headers=headers)
            self._check(status, body)

            if not body or not isinstance(body, list):
                break

            for r in body:
                results.append(r["payload"])

            if limit is not None and len(results) >= limit:
                results = results[:limit]
                break

            if len(body) < actual_page_size:
                # Reached last page
                break

            offset += len(body)

        return results

    def status(self) -> Dict[str, Any]:
        return self.config.status()


@dataclass(frozen=True)
class RemoteObjectInfo:
    size: int
    sha256: Optional[str] = None  # only when the store can report it


class ObjectStorageTransport(Protocol):
    def upload(self, bucket: str, path: str, local_file: Path, sha256: str) -> None: ...
    def head(self, bucket: str, path: str) -> Optional[RemoteObjectInfo]: ...
    def download_sha256(self, bucket: str, path: str) -> str: ...


class SupabaseStorageTransport:
    """Supabase Storage REST transport. Objects are never overwritten (x-upsert: false)."""

    def __init__(self, rest: RestTransport):
        self._rest = rest

    def upload(self, bucket: str, path: str, local_file: Path, sha256: str) -> None:
        quoted = urllib.parse.quote(path)
        status, body = self._rest.request(
            "POST", f"/storage/v1/object/{bucket}/{quoted}", raw_body=Path(local_file).read_bytes(),
            headers={"Content-Type": "application/octet-stream", "x-upsert": "false", "x-sha256": sha256},
        )
        if status == 409 or (status == 400 and "exists" in str(body).lower()):
            return  # already uploaded; integrity verified separately via head()/hash
        SupabasePersistenceBackend._check(status, body)

    def head(self, bucket: str, path: str) -> Optional[RemoteObjectInfo]:
        status, body = self._rest.request("GET", f"/storage/v1/object/info/{bucket}/{urllib.parse.quote(path)}")
        if status == 404:
            return None
        SupabasePersistenceBackend._check(status, body)
        size = (body.get("size") if isinstance(body, dict) else None) or (body.get("metadata", {}).get("size") if isinstance(body, dict) else None)
        if size is None:
            raise PersistenceError("remote object info missing size")
        return RemoteObjectInfo(size=int(size), sha256=None)

    def download_sha256(self, bucket: str, path: str) -> str:
        import hashlib

        status, body = self._rest.request("GET", f"/storage/v1/object/{bucket}/{urllib.parse.quote(path)}")
        SupabasePersistenceBackend._check(status, body)
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body).encode("utf-8")
        return hashlib.sha256(body).hexdigest()
