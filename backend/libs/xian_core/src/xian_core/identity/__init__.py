"""Agent 归属校验 / 凭据保管 / 连通性探测（PRD 3.2）。"""

from .credentials import Credential, CredentialVault
from .healthcheck import PROBES, HealthReport, ProbeResult, build_report, classify_failure
from .ownership import (
    assert_verified,
    build_dns_instruction,
    build_image_instruction,
    make_nonce,
    verify_dns,
    verify_image_digest,
)

__all__ = [
    "PROBES",
    "Credential",
    "CredentialVault",
    "HealthReport",
    "ProbeResult",
    "assert_verified",
    "build_dns_instruction",
    "build_image_instruction",
    "build_report",
    "classify_failure",
    "make_nonce",
    "verify_dns",
    "verify_image_digest",
]