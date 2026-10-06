"""归属校验、Agent 状态机、武器库导出管控、场景 DSL 校验。"""

from __future__ import annotations

import pytest
from xian_core.agents import assert_attackable, assert_transition
from xian_core.cases import can_export, load_seed_cases, select_cases
from xian_core.errors import OwnershipNotVerified, PermissionDenied, ValidationError
from xian_core.identity import build_dns_instruction, make_nonce, verify_dns, verify_image_digest
from xian_core.scenarios import all_templates, validate_dsl


def test_agent_state_machine_rejects_illegal_transitions() -> None:
    assert_transition("unverified", "active")
    assert_transition("active", "archived")
    with pytest.raises(ValidationError):
        assert_transition("archived", "active")
    with pytest.raises(ValidationError):
        assert_transition("unverified", "attacking")


class _Agent:
    def __init__(self, status: str, verified: bool) -> None:
        self.status = status
        self.ownership_verified = verified


def test_unowned_agent_cannot_be_attacked() -> None:
    """AC-09 前半：未归属 Agent 阻断演练。"""
    with pytest.raises(OwnershipNotVerified):
        assert_attackable(_Agent("active", False))


def test_offline_and_archived_agents_cannot_be_attacked() -> None:
    with pytest.raises(PermissionDenied):
        assert_attackable(_Agent("archived", True))
    with pytest.raises(PermissionDenied):
        assert_attackable(_Agent("offline", True))


def test_weapon_export_requires_admin() -> None:
    """AC-09 后半：武器库越权导出拦截。"""
    case = load_seed_cases()[0]
    assert can_export(case, role="admin") is True
    for role in ("red", "blue", "viewer"):
        assert can_export(case, role=role) is False


def test_cannot_export_unpublished_case() -> None:
    case = load_seed_cases()[0]
    case.status = "review"
    assert can_export(case, role="blue") is False


def test_dns_verification_roundtrip() -> None:
    nonce = make_nonce()
    instruction = build_dns_instruction("agent-a.corp.com", nonce)
    assert instruction["record"] == f"xian-verify={nonce}"
    failed = verify_dns("agent-a.corp.com", nonce)
    assert failed["result"] == "failed"


def test_image_digest_validation() -> None:
    bad = verify_image_digest("not-a-digest")
    assert bad["result"] == "failed"
    pending = verify_image_digest("sha256:" + "a" * 64)
    assert pending["result"] == "pending"
    ok = verify_image_digest("sha256:" + "a" * 64, "sha256:" + "a" * 64)
    assert ok["result"] == "verified"


def test_scenario_selection_by_category() -> None:
    rows = select_cases(categories=["XM-01"], limit=10)
    assert rows
    assert all(r.category_code == "XM-01" for r in rows)


def test_eight_scenario_templates_are_well_formed() -> None:
    templates = all_templates()
    assert len(templates) >= 8
    for template in templates:
        assert template.code.startswith("S"), template.code


def test_dsl_validator_accepts_bundled_scenarios() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "xian_core" / "scenarios" / "templates"
    files = sorted(root.glob("S*/scenario.yaml"))
    assert len(files) >= 8, f"应至少有 8 套场景，实际 {len(files)}"
    for path in files:
        report = validate_dsl(path.read_text(encoding="utf-8"))
        assert report.ok, f"{path.name} 校验失败：{[e.to_dict() for e in report.errors]}"


def test_dsl_validator_rejects_bad_scenario_id() -> None:
    report = validate_dsl("id: XX\nname: 非法编号\ncategory: customer_service\n")
    assert not report.ok
    assert report.errors[0].path == "$.id"
    assert report.errors[0].line >= 1
