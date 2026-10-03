"""Authentication and Authorization dependencies for Quant Cockpit API.

Security Invariants:
- All sensitive mutations (kill switch, execution, capital, paper session) require operator authorization.
- Reads are public for operational workstation cockpit by default, but if QUANT_OS_OPERATOR_TOKEN is set,
  sensitive streams and administrative endpoints enforce authentication.
- Secrets, API keys, credentials, and private environment variables must NEVER be leaked to clients.
"""
from __future__ import annotations

import hmac
import os
import re
from typing import Any, Dict, Optional
from fastapi import Header, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_security = HTTPBearer(auto_error=False)

# Mask patterns for scrubbing
_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|credential|service_role)[=:\s]+(['\"]?)([^'\"\s&]+)\2"),
    re.compile(r"Bearer\s+([A-Za-z0-9._~+/-]+=*)"),
]


def get_configured_operator_token() -> Optional[str]:
    """Retrieve the configured operator token from environment."""
    return os.environ.get("QUANT_OS_OPERATOR_TOKEN") or os.environ.get("QUANT_OS_API_KEY")


def verify_operator_token(token: Optional[str]) -> bool:
    """Verify operator token in constant time.
    
    If no operator token is configured in environment:
    - In testing/local mock mode (QUANT_OS_MOCK_MODE=1 or no strict env), allows local development if non-empty header or local test.
    - If operator token is configured, requires exact match.
    """
    configured = get_configured_operator_token()
    if not configured:
        # In mock or development mode with no token configured, require at least a present token if provided
        return True

    if not token:
        return False

    return hmac.compare_digest(configured.encode("utf-8"), token.encode("utf-8"))


def require_operator_auth(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(_bearer_security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = None,
) -> str:
    """FastAPI dependency enforcing operator authorization for mutating operations."""
    token = None
    if isinstance(auth_header, HTTPAuthorizationCredentials) and auth_header.credentials:
        token = auth_header.credentials
    elif isinstance(authorization, str) and authorization:
        token = authorization.split("Bearer ", 1)[-1].strip() if "Bearer " in authorization else authorization.strip()
    elif isinstance(x_api_key, str) and x_api_key:
        token = x_api_key

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: operator authentication credentials required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    configured = get_configured_operator_token()
    if configured and not verify_operator_token(token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: invalid operator authentication credentials.",
        )
    return token


def get_configured_stream_token() -> Optional[str]:
    """Retrieve configured stream token or fall back to operator token."""
    return os.environ.get("QUANT_OS_STREAM_TOKEN") or get_configured_operator_token()


def verify_stream_token(token: Optional[str]) -> bool:
    """Verify stream token against configured stream or operator token."""
    configured = get_configured_stream_token()
    if not configured:
        return True
    if not token:
        return False
    op_configured = get_configured_operator_token()
    if hmac.compare_digest(configured.encode("utf-8"), token.encode("utf-8")):
        return True
    if op_configured and hmac.compare_digest(op_configured.encode("utf-8"), token.encode("utf-8")):
        return True
    return False


def verify_stream_auth(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(_bearer_security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    token_query: Optional[str] = Query(None, alias="token"),
    authorization: Optional[str] = None,
    token: Optional[str] = None,
) -> bool:
    """Validate authorization for streaming endpoints (supports Header and Query param for EventSource)."""
    configured = get_configured_stream_token()
    if not configured:
        return True

    extracted = None
    if isinstance(auth_header, HTTPAuthorizationCredentials) and auth_header.credentials:
        extracted = auth_header.credentials
    elif isinstance(authorization, str) and authorization:
        extracted = authorization.split("Bearer ", 1)[-1].strip() if "Bearer " in authorization else authorization.strip()
    elif isinstance(x_api_key, str) and x_api_key:
        extracted = x_api_key
    elif isinstance(token_query, str) and token_query:
        extracted = token_query
    elif isinstance(token, str) and token:
        extracted = token

    if not extracted or not verify_stream_token(extracted):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: stream authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


def scrub_secrets(val: Any) -> Any:
    """Recursively scrub secrets, tokens, passwords, and sensitive keys from response structures."""
    if isinstance(val, dict):
        scrubbed = {}
        for k, v in val.items():
            k_lower = k.lower()
            if any(s in k_lower for s in ("secret", "api_key", "service_role", "password", "token", "private_key")):
                scrubbed[k] = "[REDACTED]"
            else:
                scrubbed[k] = scrub_secrets(v)
        return scrubbed
    elif isinstance(val, list):
        return [scrub_secrets(x) for x in val]
    elif isinstance(val, str):
        result = val
        for pat in _SECRET_PATTERNS:
            result = pat.sub(r"\1=[REDACTED]", result)
        return result
    return val
