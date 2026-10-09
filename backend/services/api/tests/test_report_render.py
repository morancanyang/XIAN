"""报告渲染与复盘引擎：九章字段 + 攻击路径图回归。"""

from __future__ import annotations

import os

os.environ.setdefault("XIAN_DB_DSN_OVERRIDE", "sqlite+aiosqlite://")

from xian_core.remediation import build_attack_path
from xian_core.reports.export import render_html, render_markdown
from xian_core.reports.render import build_report_payload


def _record(case_id: str, category: str, verdict: str) -> dict:
    return {
        "record_id": case_id,
        "category_code": category,
        "case_id": case_id,
        "case_title": f"用例 {case_id}",
        "severity": "high",
        "verdict": verdict,
        "confidence": 0.9,
        "golden_rules": [],
        "evidence": [],
        "trace_ref": f"ch://trace/{case_id}",
    }


def test_attack_path_includes_success_and_partial() -> None:
    """攻击路径图必须把 success/partial 收进链路，不能永远空图。"""
    records = [
        _record("XM-01-001", "XM-01", "success"),
        _record("XM-03-008", "XM-03", "partial"),
        _record("XM-05-001", "XM-05", "fail"),
    ]
    path = build_attack_path(subject_type="campaign", subject_id="c-1", records=records)
    labels = {str(n["label"]) for n in path["nodes"]}
    assert "用例 XM-01-001" in labels
    assert "用例 XM-03-008" in labels
    assert "用例 XM-05-001" not in labels
    assert path["edges"], "成功用例之间应连成链路"
    assert path["kill_chain"], "kill chain 不能为空"


def test_attack_path_marks_missing_stages() -> None:
    """只命中投递类用例时，其余四段都该标断裂。

    XM-01 的种子阶段是"载荷投递->初始执行"，归一到五段 kill chain 应落在 delivery；
    旧码表把它算成 recon，导致缺失阶段集合整组错位。
    """
    records = [_record("XM-01-001", "XM-01", "success")]
    path = build_attack_path(subject_type="campaign", subject_id="c-1", records=records)
    assert set(path["missing_stages"]) == {"recon", "privilege_escalation", "exfiltration", "impact"}
    assert path["kill_chain"] == ["delivery"]
    gap_ids = {str(n["id"]) for n in path["nodes"]}
    assert "gap-recon" in gap_ids


def test_report_payload_exposes_every_chapter() -> None:
    """九章各有独立字段，前端才能按章渲染而不是重复同一段内容。"""
    records = [
        _record("XM-01-001", "XM-01", "success"),
        _record("XM-05-001", "XM-05", "fail"),
    ]
    payload = build_report_payload(
        tenant_id="11111111-1111-1111-1111-111111111111",
        subject_type="campaign",
        subject_id="22222222-2222-2222-2222-222222222222",
        agent={"name": "demo", "access_type": "http", "ownership_verified": True, "baseline": {"has_rag": True}},
        records=records,
    )
    for key in (
        "executive_summary",
        "agent",
        "attack_path",
        "categories",
        "high_risk_cases",
        "findings",
        "remediation",
        "retest",
        "compliance",
    ):
        assert key in payload, f"九章缺少字段 {key}"
    assert payload["agent"]["name"] == "demo"
    assert payload["attack_path"]["nodes"], "有命中用例时攻击路径不应为空"
    assert [c["code"] for c in payload["categories"]] == ["XM-01", "XM-05"]
    assert len(payload["high_risk_cases"]) == 1


def _payload(records: list[dict], versions: list[dict] | None = None) -> dict:
    return build_report_payload(
        tenant_id="11111111-1111-1111-1111-111111111111",
        subject_type="campaign",
        subject_id="22222222-2222-2222-2222-222222222222",
        agent={"name": "demo", "access_type": "http", "ownership_verified": True, "baseline": {"has_rag": True}},
        records=records,
        versions=versions
        if versions is not None
        else [
            {"version": 1, "prompt_hash": "aaa", "source": "manual", "created_at": "2026-10-01T00:00:00", "tools": 1},
            {"version": 2, "prompt_hash": "bbb", "source": "auto", "created_at": "2026-10-02T00:00:00", "tools": 2},
        ],
    )


def test_high_risk_cases_use_case_titles() -> None:
    """第五章高危详情必须显示用例库里的中文标题，而不是只回 XM-01-001 这种代号。"""
    records = [
        _record("XM-01-001", "XM-01", "success"),
        _record("XM-01-002", "XM-01", "fail"),
    ]
    payload = _payload(records)
    assert payload["high_risk_cases"]
    for row in payload["high_risk_cases"]:
        assert row["title"] and row["title"] != row["case_id"]
    assert payload["high_risk_cases"][0]["scenario_code"] if "scenario_code" in payload["high_risk_cases"][0] else True


def test_findings_expose_root_cause_and_signals() -> None:
    """第六章根因分析：命中规则必须反查到八大根因与命中信号。"""
    records = [
        dict(_record("XM-01-001", "XM-01", "success"), golden_rules=[{"rule_id": "LOCAL-LEAK", "severity": "high"}]),
        dict(_record("XM-04-002", "XM-04", "success"), golden_rules=[{"rule_id": "G-03", "severity": "critical"}]),
        dict(_record("XM-08-001", "XM-08", "success"), golden_rules=[{"rule_id": "LOCAL-LEAK", "severity": "high"}]),
    ]
    payload = _payload(records)
    findings = payload["findings"]
    codes = {f["root_cause_code"] for f in findings}
    assert "prompt_no_isolation" in codes
    assert "tool_scope_too_wide" in codes
    for f in findings:
        assert f["root_cause_name"], "根因必须有名称"
        assert f["impact"], "根因必须有影响说明"
        assert f["affected_config"].get("value"), "根因必须有受影响配置"
        assert f["confidence"] > 0
        assert f["matched_signals"], "必须给出命中的特征信号"
        assert f["record_ids"], "必须回指触发记录"
    merged = next(f for f in findings if f["root_cause_code"] == "prompt_no_isolation")
    assert len(merged["record_ids"]) == 2, "同类根因要合并多条记录"
    assert len(payload["recommendations"]) >= len(findings)
    for rec in payload["recommendations"]:
        assert rec["playbook_ref"] and rec["priority"] and rec["effort"]
        assert rec["expected_effect"]


def test_radar_has_at_least_three_dimensions() -> None:
    """第一章雷达图至少 3 个维度，否则前端 RadarScore 直接不渲染。"""
    records = [
        _record("XM-01-001", "XM-01", "success"),
        _record("XM-04-002", "XM-04", "fail"),
        _record("XM-05-001", "XM-05", "fail"),
    ]
    payload = _payload(records)
    radar = payload["radar"]
    assert len(radar) >= 3, f"雷达维度不足：{radar}"
    assert all(0 <= v <= 100 for v in radar.values())
    assert radar.get("直接提示注入与越狱") == 0.0
    assert radar.get("过度代理/工具滥用") == 100.0


def test_retest_uses_versions_and_regression_flag() -> None:
    """第八章复测对比必须带上版本序列与回归判定。"""
    records = [_record("XM-01-001", "XM-01", "fail")]
    payload = build_report_payload(
        tenant_id="11111111-1111-1111-1111-111111111111",
        subject_type="campaign",
        subject_id="22222222-2222-2222-2222-222222222222",
        agent={"name": "demo", "access_type": "http", "ownership_verified": True, "baseline": {}},
        records=records,
        versions=[
            {"version": 1, "prompt_hash": "aaa", "source": "manual", "sec_score": 90},
            {"version": 2, "prompt_hash": "bbb", "source": "auto", "sec_score": 80},
        ],
    )
    assert len(payload["retest"]["versions"]) == 2
    assert payload["retest"]["regression_failed"] is True


def test_attack_path_labels_are_case_titles() -> None:
    """第三章攻击路径图节点要用可读标题。"""
    records = [_record("XM-01-001", "XM-01", "success"), _record("XM-05-001", "XM-05", "success")]
    payload = _payload(records)
    labels = {str(n["label"]) for n in payload["attack_path"]["nodes"]}
    assert "角色扮演式越狱（DAN 变体）" in labels
    assert payload["stage_labels"]["recon"] == "侦察"


def test_high_risk_cases_and_findings_carry_real_ids() -> None:
    """第五章要能定位到记录（trace 回放），第六章要能回指用例标题。"""
    records = [
        dict(
            _record("XM-01-001", "XM-01", "success"),
            record_id="11111111-1111-1111-1111-111111111111",
            golden_rules=[{"rule_id": "LOCAL-LEAK", "severity": "high"}],
        )
    ]
    payload = _payload(records)
    row = payload["high_risk_cases"][0]
    assert row["record_id"] == "11111111-1111-1111-1111-111111111111"
    assert row["title"] == "角色扮演式越狱（DAN 变体）"
    finding = payload["findings"][0]
    assert finding["record_ids"] == ["11111111-1111-1111-1111-111111111111"]
    assert finding["case_ids"] == ["XM-01-001"]
    assert finding["case_titles"] == ["角色扮演式越狱（DAN 变体）"]
    assert "角色扮演式越狱" in finding["impact"]
    assert finding["impact"].startswith("用例 XM-01-001"), "影响说明要可读，不能以裸 id 开头"


def test_compliance_maps_clause_names() -> None:
    """第九章必须给出可读的条款名，而不是只有 LLM01:2025 这种代号。"""
    records = [
        _record("XM-01-001", "XM-01", "success"),
        _record("XM-05-001", "XM-05", "success"),
        _record("XM-08-001", "XM-08", "fail"),
    ]
    payload = _payload(records)
    frameworks = {c["framework"]: c for c in payload["compliance"]}
    owasp = frameworks["OWASP LLM Top10 2025"]
    assert "LLM01 提示注入" in owasp["matched"]
    assert "LLM02 敏感信息泄露" in owasp["matched"]
    assert "LLM10 无界资源消耗" not in owasp["matched"], "未命中的类别不应出现在合规映射里"
    clauses = owasp["clauses"]
    assert all(c["categories"] for c in clauses), "每个条款都要能回溯到命中的类别"
    # 第三个框架此前永远为空：条款来自 frameworks.yaml，不能漏
    assert "生成式人工智能服务管理暂行办法" in frameworks


def test_export_renders_versions_without_metrics() -> None:
    """历史 payload 的版本行只有元数据：导出不能 500，也不能把缺分数当成 0 分。"""
    records = [_record("XM-01-001", "XM-01", "success"), _record("XM-04-002", "XM-04", "fail")]
    payload = _payload(records, versions=[
        {"version": "v1", "prompt_hash": "aaa", "source": "manual", "tools": 1, "created_at": "t1"},
        {"version": "v2", "prompt_hash": "bbb", "source": "auto", "tools": 2, "created_at": "t2"},
    ])
    assert payload["retest"]["regression_failed"] is False, "缺 SecScore 不该被误判成回归"
    html = render_html(payload)
    assert "v1" in html and "bbb" in html
    assert "登记时间" in html, "没有逐版本指标时要退回版本元数据列"
    assert "<th>SecScore</th>" not in html, "没有逐版本指标时不应画 SecScore 列"
    md = render_markdown(payload)
    assert "| 版本快照 |" in md
    assert "暂未携带逐版本" in md


def test_export_renders_version_metrics_when_present() -> None:
    """调用方真的带了逐版本指标时，第八章要画指标列而不是丢数据。"""
    records = [_record("XM-01-001", "XM-01", "success")]
    payload = _payload(records, versions=[
        {"version": "v1", "sec_score": 90, "asr": 0.1, "baseline_pass_rate": 0.95},
        {"version": "v2", "sec_score": 80, "asr": 0.2, "baseline_pass_rate": 0.9},
    ])
    assert payload["retest"]["regression_failed"] is True
    chapter = render_html(payload).split("八、复测对比")[1].split("</section>")[0]
    assert "90" in chapter and "10.0%" in chapter and "95.0%" in chapter
    assert "检测到回归" in chapter


def test_export_high_risk_cases_render_rule_and_evidence() -> None:
    """第五章要渲染命中规则与判定依据，不能留下空 payload 块和 dict repr。"""
    records = [
        dict(
            _record("XM-01-001", "XM-01", "success"),
            golden_rules=[{"rule_id": "G-08", "severity": "critical", "detail": "蜜标外泄"}],
            evidence=[{"pattern": "sk-canary-", "matched_text": "sk-canary-demo"}],
        )
    ]
    payload = _payload(records)
    html = render_html(payload)
    assert "G-08" in html and "蜜标外泄" in html
    assert "sk-canary-demo" in html
    assert "{'rule_id'" not in html, "命中规则不能渲染成 Python dict repr"
    md = render_markdown(payload)
    assert "G-08" in md and "sk-canary-demo" in md
