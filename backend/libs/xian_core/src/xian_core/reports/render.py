"""九章报告渲染（PRD 3.8.4.1）：把战役/会话产出汇总为结构化章节数据。"""

from __future__ import annotations

import itertools
import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from ..cases import get_case
from ..matrix import framework_names, load_categories, load_frameworks
from ..remediation import (
    build_attack_path,
    build_recommendations,
    cause_by_id,
    load_root_causes,
    locate_root_causes,
    merge_findings,
)
from ..schemas.scoring import ScoreInput
from ..scoring import build_benchmark, compute_score, grade_of, segment_for

#: 黄金规则 / 本地裁判规则 → 根因特征信号（PRD 3.7.4.8.1 规则模板匹配）
RULE_SIGNALS: dict[str, list[str]] = {
    "G-01": ["canary_missed"],
    "G-02": ["canary_in_output"],
    "G-03": ["unauthorized_tool_call", "tool_scope_write_or_exec"],
    "G-04": ["tool_param_match_canary", "param_tampered"],
    "G-05": ["canary_missed"],
    "G-06": ["tool_scope_write_or_exec"],
    "G-07": ["encoded_leak"],
    "G-08": ["pii_in_output"],
    "G-09": ["memory_poison"],
    "G-10": ["resource_exhaustion", "no_circuit_breaker"],
    # G-11 是目标自身上报的蜜标命中：既可能是输出带出了蜜标，也可能是调了高危工具，
    # 因此同时映射到输出过滤与工具权限两类根困信号。
    "G-11": ["canary_in_output", "unauthorized_tool_call"],
    "CASE-CRITERIA": ["unauthorized_tool_call"],
    "LOCAL-LEAK": ["system_prompt_disclosed", "prompt_markers_hit"],
    "LOCAL-COMPLY": ["system_prompt_disclosed"],
    "LOCAL-ECHO": ["prompt_markers_hit"],
    "LOCAL-REFUSE": [],
}

STAGE_LABELS = {
    "recon": "侦察",
    "delivery": "载荷投递",
    "privilege_escalation": "提权",
    "exfiltration": "渗出",
    "impact": "影响",
}

CHAPTERS = (
    "执行摘要",
    "Agent 画像与攻击面清单",
    "攻击路径图",
    "分类别结果",
    "高危详情",
    "根因分析与修复建议",
    "整改清单",
    "复测对比",
    "合规映射",
)


def build_report_payload(
    *,
    tenant_id: str,
    subject_type: str,
    subject_id: str,
    agent: dict[str, Any],
    records: Iterable[dict[str, Any]],
    versions: Iterable[dict[str, Any]] | None = None,
    baseline_pass_rate: float = 1.0,
    minscore: int = 0,
) -> dict[str, Any]:
    rows = [_enrich_record(r) for r in records]
    total = len(rows)
    successes = [r for r in rows if str(r.get("verdict")) == "success"]
    asr = round(len(successes) / total, 4) if total else 0.0

    categories = load_categories()
    category_rows: list[dict[str, Any]] = []
    for cat in categories:
        subset = [r for r in rows if r.get("category_code") == cat.code]
        if not subset:
            continue
        succ = [r for r in subset if str(r.get("verdict")) == "success"]
        severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        worst = max((r.get("severity", "low") for r in subset), key=lambda s: severity_rank.get(s, 0))
        category_rows.append(
            {
                "code": cat.code,
                "name": cat.name,
                "total": len(subset),
                "success": len(succ),
                "asr": round(len(succ) / len(subset), 4),
                "max_severity": worst,
            }
        )

    category_results: dict[str, list[Any]] = {}
    severity_by_category: dict[str, str] = {}
    difficulty_by_category: dict[str, str] = {}
    for cat in categories:
        subset = [r for r in rows if r.get("category_code") == cat.code]
        if not subset:
            continue
        category_results[cat.code] = [
            ("success" if str(r.get("verdict")) == "success" else "fail") for r in subset
        ]
        severity_by_category[cat.code] = worst_severity(subset)
        difficulty_by_category[cat.code] = cat.difficulty
    scenario_codes = [str(r.get("scenario_code", "")) for r in rows if r.get("scenario_code")]
    score_value = compute_score(
        ScoreInput(
            subject_type=subject_type,
            subject_id=uuid.UUID(subject_id) if _is_uuid(subject_id) else uuid.uuid4(),
            segment=segment_for(scenario_codes),
            category_results=category_results,
        ),
        severity_by_category=severity_by_category,
        difficulty_by_category=difficulty_by_category,
    ).sec_score

    findings_raw = merge_findings([_finding_row(r, subject_id=subject_id) for r in successes])
    recommendations = build_recommendations(findings_raw)
    findings = [
        {
            "id": str(f["id"]),
            "root_cause_code": f["root_cause_code"],
            "root_cause_name": f.get("root_cause_name", ""),
            "severity": f["severity"],
            "affected_config": f["affected_config"],
            "impact": f.get("impact", ""),
            "confidence": float(f.get("confidence", 0.0)),
            "matched_signals": list(f.get("matched_signals", [])),
            "primary": bool(f.get("primary", False)),
            "record_ids": list(f.get("record_ids", [])),
            "case_ids": list(f.get("case_ids", [])),
            "case_titles": list(f.get("case_titles", [])),
            "trace_refs": list(f.get("trace_refs", [])),
            "evidence": f["evidence"],
            "recommendations": [
                {
                    "id": str(rec.id),
                    "priority": rec.priority,
                    "playbook_ref": rec.playbook_ref,
                    "effort": rec.effort,
                    "expected_effect": rec.expected_effect,
                    "side_effects": rec.side_effects,
                }
                for rec in recommendations
                if str(rec.finding_id) == str(f["id"])
            ],
        }
        for f in findings_raw
    ]
    recommendation_rows = [
        {
            "id": str(rec.id),
            "finding_root_cause": str(f["root_cause_code"]),
            "severity": str(f["severity"]),
            "priority": rec.priority,
            "effort": rec.effort,
            "playbook_ref": rec.playbook_ref,
            "expected_effect": rec.expected_effect,
            "side_effects": rec.side_effects,
            "applied": bool(rec.applied),
            "artifacts": len(rec.diff_payload.get("artifacts", []) or []),
        }
        for f in findings_raw
        for rec in recommendations
        if str(rec.finding_id) == str(f["id"])
    ]

    versions_rows = list(versions or [])
    benchmark = build_benchmark([score_value], segment=segment_for(scenario_codes, str(agent.get("agent_form", ""))))

    return {
        "id": _fake_uuid(subject_id),
        "tenant_id": tenant_id,
        "title": f"AI Agent 安全演练报告 · {agent.get('name', '')}",
        "subject_type": subject_type,
        "subject_id": subject_id,
        "sec_score": score_value,
        "grade": grade_of(score_value),
        "asr": asr,
        "baseline_pass_rate": baseline_pass_rate,
        "created_at": datetime.now().astimezone(),
        "executive_summary": (
            f"本次演练共执行 {total} 条攻击用例，命中 {len(successes)} 条（ASR {asr:.1%}）。"
            f"综合安全分为 {score_value}（{grade_of(score_value)} 级）。"
            f"识别出 {len(findings_raw)} 类根因、{len(recommendations)} 项整改建议。"
            f"可用性基线通过率 {baseline_pass_rate:.0%}。"
        ),
        "top_risks": [
            {
                "severity": f["severity"],
                "title": f.get("root_cause_name") or f["affected_config"].get("value", f["root_cause_code"]),
                "case_id": str(((f.get("case_ids") or [""]) or [""])[0]),
                "root_cause": f["root_cause_code"],
                "confidence": float(f.get("confidence", 0.0)),
            }
            for f in sorted(
                findings_raw,
                key=lambda x: (
                    {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 9),
                    -float(x.get("confidence", 0.0)),
                ),
            )[:3]
        ],
        "agent": agent,
        "attack_path": build_attack_path(subject_type=subject_type, subject_id=subject_id, records=rows),
        "stage_labels": STAGE_LABELS,
        "radar": _radar(category_rows),
        "categories": category_rows,
        "total_categories": len(categories),
        "high_risk_cases": [
            {
                "record_id": str(r.get("record_id", "")),
                "case_id": r.get("case_id", ""),
                "title": r.get("case_title", ""),
                "category_code": r.get("category_code", ""),
                "severity": r.get("severity", "medium"),
                "verdict": r.get("verdict", ""),
                "confidence": float(r.get("confidence", 0.0)),
                "strategy": r.get("strategy", ""),
                "turns": int(r.get("turns", 0) or 0),
                "tokens": int(r.get("tokens", 0) or 0),
                "mutation_ops": list(r.get("mutation_ops", [])),
                "golden_rules": list(r.get("golden_rules", [])),
                "evidence": list(r.get("evidence", [])),
                "trace_ref": r.get("trace_ref", ""),
            }
            for r in successes
        ],
        "findings": findings,
        "recommendations": recommendation_rows,
        "remediation": {
            "matrix": _matrix(recommendations),
            "total": len(recommendations),
        },
        "retest": {
            "versions": versions_rows,
            "regression_failed": _regression_failed(versions_rows),
        },
        "compliance": _compliance(rows),
        "benchmark": benchmark,
        "min_score_gate": minscore,
    }


def _matrix(recommendations: Iterable[Any]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {}
    for rec in recommendations:
        matrix.setdefault(str(rec.priority), {}).setdefault(str(rec.effort), 0)
        matrix[str(rec.priority)][str(rec.effort)] += 1
    return matrix


def _enrich_record(record: dict[str, Any]) -> dict[str, Any]:
    """用攻击用例库回填报告可读字段：用例标题 / 场景代号 / 用例严重度（PRD 3.8.4 第 4-6 章）。"""
    row = dict(record)
    case = get_case(str(row.get("case_id", "")))
    # 用例库标题优先：报告里要出现人能读懂的用例名，而不是只回代号
    row["case_title"] = str((case.title if case else "") or row.get("case_title") or row.get("case_id", ""))
    row["case_severity"] = str((case.severity if case else "") or row.get("severity") or "medium")
    row["scenario_code"] = str(
        row.get("scenario_code") or (case.scenario_tags[0] if case and case.scenario_tags else "")
    )
    row["severity"] = str(row.get("severity") or row["case_severity"] or "medium")
    return row


def signals_of(record: dict[str, Any]) -> list[str]:
    """命中规则 → 根因特征信号（PRD 3.7.4.8.1 规则模板匹配）。"""
    out: list[str] = []
    for hit in record.get("golden_rules") or []:
        rule_id = str(hit.get("rule_id", "")) if isinstance(hit, dict) else str(hit)
        for signal in RULE_SIGNALS.get(rule_id, []):
            if signal not in out:
                out.append(signal)
    return out


def _finding_row(record: dict[str, Any], *, subject_id: str) -> dict[str, Any]:
    """单条命中记录 → 发现行：用规则信号反查八大根因（PRD 3.7.4.8.1）。"""
    signals = signals_of(record)
    matched = locate_root_causes(signals)
    row: dict[str, Any] = {
        "id": _fake_uuid(str(record.get("record_id", ""))),
        "campaign_id": subject_id,
        "record_ids": [str(record.get("record_id", ""))],
        "case_ids": [str(record.get("case_id", ""))],
        "case_titles": [str(record.get("case_title", ""))],
        "trace_refs": [str(record.get("trace_ref", ""))],
        "evidence": list(record.get("evidence") or []),
        "matched_signals": signals,
        "confidence": float(record.get("confidence", 0.0) or 0.0),
    }
    if matched:
        top = matched[0]
        cause = cause_by_id(str(top["root_cause_id"])) or {}
        row.update(
            {
                "root_cause_code": str(top["root_cause_id"]),
                "root_cause_name": str(top["name"]),
                "severity": str(top["severity"]),
                "affected_config": {"kind": str(top["category"]), "value": str(top["affected_config"])},
                "impact": (
                    f"用例 {row['case_ids'][0] or '未知'}（{row['case_titles'][0] or '未命名用例'}）"
                    f"命中「{top['name']}」：{cause.get('description', '')}"
                    f"受影响配置：{top['affected_config']}。"
                ),
                "confidence": float(top["confidence"]),
                "matched_signals": list(top["matched_signals"]),
            }
        )
        return row
    row.update(
        {
            "root_cause_code": "unmapped",
            "root_cause_name": "未定位到已知根因",
            "severity": str(record.get("severity", "medium")),
            "affected_config": {"kind": "unknown", "value": "待人工复核"},
            "impact": "命中判定成立，但规则信号未映射到八大根因，建议人工复核并补充规则模板。",
        }
    )
    return row


def _radar(category_rows: list[dict[str, Any]]) -> dict[str, float]:
    """分类别得分雷达：1 - ASR 换算百分制，至少 3 个维度雷达图才有意义。"""
    return {str(row["name"]): round((1.0 - float(row["asr"])) * 100, 1) for row in category_rows}


def _regression_failed(versions: list[dict[str, Any]]) -> bool:
    """AC-11：SecScore 跌幅 > 5 分判 fail。"""
    if len(versions) < 2:
        return False
    ordered = sorted(versions, key=lambda v: str(v.get("version", "")))
    for prev, cur in itertools.pairwise(ordered):
        if float(prev.get("sec_score", 0)) - float(cur.get("sec_score", 0)) > 5:
            return True
    return False


def _compliance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """合规映射（PRD 3.8.4 第九章）：命中类别 → 框架条款，条款名可读、可回溯到类别。"""
    hit_codes = sorted(
        {str(r.get("category_code")) for r in rows if str(r.get("verdict")) == "success" and r.get("category_code")}
    )
    out: list[dict[str, Any]] = []
    for framework in framework_names():
        clauses: list[dict[str, Any]] = []
        for clause in load_frameworks().get(framework, []):
            overlap = [c for c in clause.get("category_ids", []) if c in hit_codes]
            if overlap:
                clauses.append({"clause": str(clause.get("clause", "")), "categories": overlap})
        out.append(
            {
                "framework": framework,
                "clauses": clauses,
                "matched": [str(c["clause"]) for c in clauses],
                "hit_categories": hit_codes,
            }
        )
    return out


def _fake_uuid(text: str) -> str:
    import hashlib
    import uuid

    return str(uuid.UUID(hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]))

def worst_severity(rows: list[dict[str, Any]]) -> str:
    rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    if not rows:
        return "low"
    return max((str(r.get("severity", "low")) for r in rows), key=lambda s: rank.get(s, 0))


def _is_uuid(text: str) -> bool:
    try:
        uuid.UUID(str(text))
    except (ValueError, AttributeError, TypeError):
        return False
    return True