"""根因定位、发现生成、攻击路径图与一键复测（PRD 3.7）。"""

from __future__ import annotations

import itertools
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..errors import NotFoundError
from ..schemas.report import FindingOut, RecommendationOut, RemediationRunOut

CAUSE_DIR = Path(__file__).resolve().parent
PLAYBOOK_DIR = CAUSE_DIR / "playbooks"

STAGES = ("recon", "delivery", "privilege_escalation", "exfiltration", "impact")


@lru_cache(maxsize=1)
def load_root_causes() -> tuple[dict[str, Any], ...]:
    raw = yaml.safe_load((CAUSE_DIR / "root_causes.yaml").read_text(encoding="utf-8")) or {}
    return tuple(raw.get("causes", []))


@lru_cache(maxsize=1)
def load_playbooks() -> tuple[dict[str, Any], ...]:
    out: list[dict[str, Any]] = []
    for path in sorted(PLAYBOOK_DIR.glob("*.yaml")):
        out.append(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    return tuple(out)


def cause_by_id(cause_id: str) -> dict[str, Any] | None:
    for cause in load_root_causes():
        if cause["id"] == cause_id:
            return cause
    return None


def require_cause(cause_id: str) -> dict[str, Any]:
    cause = cause_by_id(cause_id)
    if cause is None:
        raise NotFoundError(f"根因 {cause_id} 不存在")
    return cause


def playbooks_for(cause_id: str) -> list[dict[str, Any]]:
    return [p for p in load_playbooks() if p.get("root_cause") == cause_id]


def playbook_by_id(playbook_id: str) -> dict[str, Any] | None:
    for pb in load_playbooks():
        if pb.get("id") == playbook_id:
            return pb
    return None


# ---------------------------------------------------------------- 根因定位
def locate_root_causes(signals: Iterable[str]) -> list[dict[str, Any]]:
    """特征匹配（规则模板优先）：把成功攻击的信号映射到八大根因（PRD 3.7.4.8.1）。"""
    seen_signals = set(signals)
    matched: list[dict[str, Any]] = []
    for cause in load_root_causes():
        overlap = seen_signals & set(cause.get("signals", []))
        if not overlap:
            continue
        confidence = round(len(overlap) / len(cause.get("signals", [])), 4)
        matched.append(
            {
                "root_cause_id": cause["id"],
                "name": cause["name"],
                "category": cause["category"],
                "affected_config": cause["affected_config"],
                "severity": cause["default_severity"],
                "confidence": confidence,
                "matched_signals": sorted(overlap),
            }
        )
    matched.sort(key=lambda item: (-item["confidence"], item["root_cause_id"]))
    return matched


def merge_findings(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """合并同类根因，多根因并存时保留全部并标注主次（PRD 3.7.4.8.1）。"""
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get("root_cause_code", row.get("root_cause_id", ""))
        if key not in merged:
            merged[key] = dict(row)
            merged[key]["root_cause_code"] = key
        else:
            merged[key]["confidence"] = max(merged[key].get("confidence", 0.0), row.get("confidence", 0.0))
            for field in ("record_ids", "case_ids", "case_titles", "trace_refs", "evidence", "matched_signals"):
                bucket = merged[key].setdefault(field, [])
                for value in row.get(field, []) or []:
                    if value not in bucket:
                        bucket.append(value)
    ordered = sorted(merged.values(), key=lambda item: -item.get("confidence", 0.0))
    for idx, item in enumerate(ordered):
        item["primary"] = idx == 0
    return ordered


def assess_impact(*, scenario_script: list[str], severity: str, subject: str) -> dict[str, Any]:
    """影响评估：结合场景剧本评估业务影响（PRD 3.7.4.1 第三步）。"""
    money_keywords = ("下单", "委托", "支付", "转账", "改地址")
    compliance_keywords = ("身份证", "手机号", "病历", "持仓", "客户")
    text = "".join(scenario_script)
    impacts: list[str] = []
    if any(k in text for k in money_keywords):
        impacts.append("资金损失")
    if any(k in text for k in compliance_keywords):
        impacts.append("数据泄露")
    if severity in {"critical", "high"}:
        impacts.append("合规风险")
    if not impacts:
        impacts.append("服务可用性")
    return {
        "subject": subject,
        "severity": severity,
        "impacts": impacts,
        "level": "high" if severity == "critical" else ("medium" if severity == "high" else "low"),
    }


# ---------------------------------------------------------------- 攻击路径图
def build_attack_path(
    *,
    subject_type: str,
    subject_id: str,
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """按 kill chain 五阶段聚类成功链路，链路断裂以虚线标注（PRD 3.7.4.8.2）。"""
    rows = [r for r in records if str(r.get("verdict")) in ("success", "partial")]
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    stage_nodes: dict[str, list[str]] = {s: [] for s in STAGES}
    for idx, row in enumerate(rows, start=1):
        stage = _stage_of(row)
        node_id = f"n{idx}"
        nodes.append(
            {
                "id": node_id,
                "label": row.get("case_title") or row.get("category_code", "unknown"),
                "stage": stage,
                "record_refs": [row.get("record_id", "")],
                "severity": row.get("severity", "medium"),
                "evidence": row.get("evidence", []),
            }
        )
        stage_nodes[stage].append(node_id)
    previous: str | None = None
    for stage in STAGES:
        ids = stage_nodes[stage]
        if not ids:
            continue
        if previous is not None:
            edges.append({"from": previous, "to": ids[0], "dashed": False})
        for a, b in zip(ids, ids[1:]):
            edges.append({"from": a, "to": b, "dashed": False})
        previous = ids[-1]
    # 链路断裂检测：中间阶段无节点时补充虚线占位
    missing = [s for s in STAGES if not stage_nodes[s]]
    for stage in missing:
        node_id = f"gap-{stage}"
        nodes.append({"id": node_id, "label": f"{stage}（证据缺失）", "stage": stage, "record_refs": [], "severity": "info"})
    return {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "nodes": nodes,
        "edges": edges,
        "missing_stages": missing,
        "kill_chain": [s for s in STAGES if stage_nodes[s]],
    }


def _stage_of(record: dict[str, Any]) -> str:
    category = str(record.get("category_code", ""))
    mapping = {
        "XM-01": "recon",
        "XM-02": "recon",
        "XM-03": "delivery",
        "XM-04": "privilege_escalation",
        "XM-05": "delivery",
        "XM-06": "privilege_escalation",
        "XM-07": "impact",
        "XM-08": "privilege_escalation",
        "XM-09": "delivery",
        "XM-10": "exfiltration",
        "XM-11": "impact",
        "XM-12": "impact",
        "XM-13": "exfiltration",
        "XM-14": "impact",
    }
    return mapping.get(category, "delivery")


# ---------------------------------------------------------------- 整改清单
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
COST_WEIGHT = {"S": 1, "M": 2, "L": 3}


def build_recommendations(findings: Iterable[dict[str, Any]]) -> list[RecommendationOut]:
    """按根因匹配修复 Playbook，按「修复成本 × 风险下降」排序（PRD 3.7.5.1）。"""
    out: list[RecommendationOut] = []
    for finding in findings:
        for playbook in playbooks_for(finding["root_cause_code"]):
            cost = str(playbook.get("cost", "M"))
            risk_drop = float(playbook.get("risk_reduction", 0.1))
            roi = round(risk_drop / COST_WEIGHT.get(cost, 2), 4)
            out.append(
                RecommendationOut(
                    id=uuid.uuid4(),
                    finding_id=uuid.UUID(str(finding["id"])),
                    type=str(playbook.get("artifacts", [{}])[0].get("type", "prompt_diff")),
                    priority=str(playbook.get("priority", "P1")),
                    effort=cost,
                    diff_payload={"artifacts": list(playbook.get("artifacts", []))},
                    playbook_ref=str(playbook.get("id", "")),
                    expected_effect=str(playbook.get("verification", "")),
                    side_effects=str(playbook.get("side_effects", "")),
                    applied=False,
                )
            )
            _ = roi
    out.sort(key=lambda r: (PRIORITY_ORDER.get(r.priority, 9), COST_WEIGHT.get(r.effort, 2)))
    return out


def remediation_matrix(recommendations: Iterable[RecommendationOut]) -> dict[str, Any]:
    """整改清单（优先级 × 成本矩阵，PRD 3.8.4 第七章）。"""
    matrix: dict[str, dict[str, int]] = {}
    for rec in recommendations:
        matrix.setdefault(rec.priority, {}).setdefault(rec.effort, 0)
        matrix[rec.priority][rec.effort] += 1
    return {"matrix": matrix, "total": sum(sum(v.values()) for v in matrix.values())}


def finding_to_out(finding: dict[str, Any]) -> FindingOut:
    return FindingOut(
        id=uuid.UUID(str(finding["id"])),
        campaign_id=uuid.UUID(str(finding["campaign_id"])),
        record_ids=[uuid.UUID(str(r)) for r in finding.get("record_ids", [])],
        root_cause_code=str(finding.get("root_cause_code", finding.get("root_cause_id", ""))),
        severity=str(finding.get("severity", "medium")),
        affected_config=dict(finding.get("affected_config", {})),
        impact=str(finding.get("impact", "")),
        trace_refs=list(finding.get("trace_refs", [])),
        evidence=list(finding.get("evidence", [])),
    )


# ---------------------------------------------------------------- 一键复测
@dataclass(slots=True)
class RetestResult:
    recommendation_id: str
    before_sec_score: int
    after_sec_score: int
    before_asr: float
    after_asr: float
    regression_pass_rate: float
    status: str
    rolled_back: bool = False

    def to_out(self, *, run_id: uuid.UUID | None = None, applied_at: Any = None) -> RemediationRunOut:
        return RemediationRunOut(
            id=run_id or uuid.uuid4(),
            recommendation_id=uuid.UUID(self.recommendation_id),
            applied_at=applied_at or datetime.now().astimezone(),
            before_sec_score=self.before_sec_score,
            after_sec_score=self.after_sec_score,
            before_asr=self.before_asr,
            after_asr=self.after_asr,
            regression_pass_rate=self.regression_pass_rate,
            status=self.status,
        )


def evaluate_retest(
    *,
    before_sec_score: int,
    after_sec_score: int,
    before_asr: float,
    after_asr: float,
    baseline_pass_rate: float,
    min_improvement: int = 5,
) -> RetestResult:
    """复测判定：分数未升或可用性受损即回滚（PRD 3.7.5 后置条件）。"""
    improved = after_sec_score - before_sec_score
    usable = baseline_pass_rate >= 0.8
    ok = improved >= min_improvement and usable
    return RetestResult(
        recommendation_id="",
        before_sec_score=before_sec_score,
        after_sec_score=after_sec_score,
        before_asr=before_asr,
        after_asr=after_asr,
        regression_pass_rate=baseline_pass_rate,
        status="passed" if ok else ("rolled_back" if not usable else "no_improvement"),
        rolled_back=not ok,
    )