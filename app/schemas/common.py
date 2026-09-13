"""Shared enums used across request/response schemas.

Per ARCHITECTURE.md Section 6, ``protocol`` is a fixed enum. ``Severity``
and ``AttackType`` (also named in Section 2's directory layout) belong to
the alerting model introduced in Phase 2 and are intentionally not added
yet, since Phase 0 does not create alerts.
"""

from enum import Enum


class Protocol(str, Enum):
    tcp = "tcp"
    udp = "udp"
    icmp = "icmp"
    http = "http"
    https = "https"
    other = "other"
