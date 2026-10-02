"""Resilient DNS resolution patch for environments where local ISP/router DNS fails to resolve Polymarket."""
import socket
import logging

logger = logging.getLogger("dns_patch")

# Cloudflare Anycast IPs for Polymarket edge
POLYMARKET_FALLBACK_IPS = ["172.64.153.51", "104.18.34.205"]

_orig_getaddrinfo = socket.getaddrinfo


def apply_dns_fallback() -> None:
    """Monkeypatches socket.getaddrinfo to provide resilient resolution for Polymarket domains."""
    def patched_getaddrinfo(host, port, *args, **kwargs):
        try:
            return _orig_getaddrinfo(host, port, *args, **kwargs)
        except socket.gaierror:
            if isinstance(host, str) and "polymarket.com" in host:
                logger.info(f"Local DNS failed for {host}. Applying resilient fallback IP {POLYMARKET_FALLBACK_IPS[0]}")
                # Return synthetic getaddrinfo result pointing to Cloudflare edge IP
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (POLYMARKET_FALLBACK_IPS[0], port))]
            raise

    socket.getaddrinfo = patched_getaddrinfo
