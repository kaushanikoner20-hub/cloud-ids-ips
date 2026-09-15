"""Shared enums used across request/response schemas.

Per ARCHITECTURE.md Section 6, ``protocol`` is a fixed enum. ``Severity``
and ``AttackType`` are added here in Phase 1 because the read-only
``GET /alerts`` response shape and query filters need them, even though
no alert-creation logic exists until Phase 2 (Section 6 / 5.2).
"""

from enum import Enum


class Protocol(str, Enum):
    tcp = "tcp"
    udp = "udp"
    icmp = "icmp"
    http = "http"
    https = "https"
    other = "other"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AttackType(str, Enum):
    benign = "benign"
    ddos_volumetric = "ddos_volumetric"
    brute_force = "brute_force"
    port_scan = "port_scan"
    anomaly = "anomaly"
    mixed = "mixed"