"""Partition manifest and SHA256 checksum manager."""
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import os


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hex digest for a given file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class PartitionManifest:
    """Manages manifest.json for an hourly partition directory."""

    def __init__(self, partition_dir: Path):
        self.partition_dir = partition_dir
        self.manifest_file = partition_dir / "manifest.json"

    def record_part(self, part_filename: str, row_count: int, byte_size: int, sha256_hash: str) -> None:
        """Atomically record a new parquet part into manifest.json."""
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
        """Read existing manifest or return initialized structure."""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "partition": str(self.partition_dir),
            "parts": [],
            "total_parts": 0,
            "total_rows": 0,
            "total_bytes": 0,
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
