"""Helpers for request identity and fixed-window abuse controls."""

import ipaddress

from django.conf import settings
from django.core.cache import cache


def get_client_ip(request):
    """Return the client address, trusting a proxy header only when configured."""
    header_name = getattr(settings, "RATE_LIMIT_CLIENT_IP_HEADER", "")
    forwarded_ip = request.META.get(header_name, "") if header_name else ""
    candidates = [forwarded_ip.strip(), request.META.get("REMOTE_ADDR", "")]
    for candidate in candidates:
        try:
            return ipaddress.ip_address(candidate).compressed
        except ValueError:
            continue
    return "unknown"


def increment_rate_limit(key, timeout):
    """Atomically increment a cache counter while preserving its first expiry."""
    if cache.add(key, 1, timeout):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        # The key may expire between the failed add and increment.
        cache.add(key, 1, timeout)
        return 1
