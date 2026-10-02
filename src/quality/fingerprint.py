"""Deterministic configuration fingerprinting for Batch 0 recorder."""
import hashlib
import json
from typing import Dict, Any, Optional

from config.settings import Settings, settings as default_settings


def canonicalize_config(cfg: Optional[Settings] = None) -> Dict[str, Any]:
    """Extract and sort canonical configuration attributes, excluding secrets."""
    c = cfg or default_settings
    return {
        "binance": {
            "initial_calibration_sample_v0": sorted(c.binance.initial_calibration_sample_v0),
            "market_ws_url": str(c.binance.market_ws_url).strip(),
            "max_retries": int(c.binance.max_retries),
            "oi_poller_interval_sec": float(c.binance.oi_poller_interval_sec),
            "public_ws_url": str(c.binance.public_ws_url).strip(),
            "request_timeout_sec": float(c.binance.request_timeout_sec),
            "rest_base_url": str(c.binance.rest_base_url).strip(),
            "symbol_type_filter": int(c.binance.symbol_type_filter),
        },
        "deribit": {
            "heartbeat_interval_sec": float(c.deribit.heartbeat_interval_sec),
            "index_channels": sorted(c.deribit.index_channels),
            "max_expiry_days": int(c.deribit.max_expiry_days),
            "moneyness_max": float(c.deribit.moneyness_max),
            "moneyness_min": float(c.deribit.moneyness_min),
            "rest_url": str(c.deribit.rest_url).strip(),
            "trade_channels": sorted(c.deribit.trade_channels),
            "ws_url": str(c.deribit.ws_url).strip(),
        },
        "polymarket": {
            "clob_api_url": str(c.polymarket.clob_api_url).strip(),
            "crypto_keywords": sorted(c.polymarket.crypto_keywords),
            "custom_events": sorted(c.polymarket.custom_events),
            "custom_feature_enabled": bool(c.polymarket.custom_feature_enabled),
            "discovery_interval_sec": float(c.polymarket.discovery_interval_sec),
            "gamma_api_url": str(c.polymarket.gamma_api_url).strip(),
            "heartbeat_interval_sec": float(c.polymarket.heartbeat_interval_sec),
            "standard_events": sorted(c.polymarket.standard_events),
            "ws_url": str(c.polymarket.ws_url).strip(),
        },
        "storage": {
            "compression": str(c.storage.compression).lower().strip(),
            "compression_level": int(c.storage.compression_level),
            "flush_interval_sec": float(c.storage.flush_interval_sec),
            "flush_row_threshold": int(c.storage.flush_row_threshold),
            "manifest_enabled": bool(c.storage.manifest_enabled),
        },
    }


def compute_config_fingerprint(cfg: Optional[Settings] = None) -> str:
    """Compute deterministic SHA-256 fingerprint for recorder configuration."""
    canonical_dict = canonicalize_config(cfg)
    serialized = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
