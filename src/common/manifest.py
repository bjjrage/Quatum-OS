"""Partition manifest and SHA256 checksum manager.

Fail-Closed Invariants:
- A corrupt or structurally invalid manifest.json MUST fail closed (raise ManifestCorruptError).
- It must NEVER be silently recreated as an empty manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hex digest for a given file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class ManifestCorruptError(RuntimeError):
    """Raised when a partition manifest exists on disk but is corrupt or invalid."""
    pass


class PartitionManifest:
    """Manages manifest.json for an hourly partition directory."""

    def __init__(self, partition_dir: Path):
        self.partition_dir = Path(partition_dir)
        self.manifest_file = self.partition_dir / "manifest.json"

    def record_part(self, part_filename: str, row_count: int, byte_size: int, sha256_hash: str) -> None:
        """Atomically record a new parquet part into manifest.json.
        
        Raises ManifestCorruptError if existing manifest on disk is corrupt.
        """
        manifest_data = self._read_manifest()
        
        part_entry = {
            "part_filename": part_filename,
            "row_count": row_count,
            "byte_size": byte_size,
            "sha256": sha256_hash,
            "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
        # Avoid duplicate part entries
        existing_filenames = {p["part_filename"] for p in manifest_data["parts"]}
        if part_filename not in existing_filenames:
            manifest_data["parts"].append(part_entry)
            
        manifest_data["last_updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest_data["total_parts"] = len(manifest_data["parts"])
        manifest_data["total_rows"] = sum(p["row_count"] for p in manifest_data["parts"])
        manifest_data["total_bytes"] = sum(p["byte_size"] for p in manifest_data["parts"])

        # Write atomically via temp file
        tmp_manifest = self.partition_dir / f".manifest-{os.getpid()}.tmp"
        with open(tmp_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        os.replace(tmp_manifest, self.manifest_file)

    def _read_manifest(self) -> Dict[str, Any]:
        """Read existing manifest or return initialized structure.
        
        Fail-closed: raises ManifestCorruptError if file exists but contains invalid JSON
        or invalid structure.
        """
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    content = f.read()
                data = json.loads(content)
                if not isinstance(data, dict) or "parts" not in data or not isinstance(data["parts"], list):
                    raise ManifestCorruptError(
                        f"Partition manifest at {self.manifest_file} is structurally invalid"
                    )
                return data
            except (json.JSONDecodeError, UnicodeDecodeError, ManifestCorruptError) as exc:
                raise ManifestCorruptError(
                    f"Partition manifest at {self.manifest_file} is corrupted: {exc}"
                ) from exc

        return {
            "partition": str(self.partition_dir),
            "parts": [],
            "total_parts": 0,
            "total_rows": 0,
            "total_bytes": 0,
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    def verify(self) -> Tuple[bool, Optional[str]]:
        """Verify partition manifest integrity without modifying it."""
        try:
            data = self._read_manifest()
            for part in data.get("parts", []):
                part_path = self.partition_dir / part["part_filename"]
                if not part_path.exists():
                    return False, f"Missing part file referenced in manifest: {part['part_filename']}"
                if part_path.stat().st_size != part.get("byte_size"):
                    return False, f"Byte size mismatch for {part['part_filename']}"
            return True, None
        except ManifestCorruptError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected verification failure: {e}"
