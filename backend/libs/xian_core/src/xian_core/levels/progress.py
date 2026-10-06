"""关卡进度、能量、徽章与段位（PRD 3.4.5）。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .fixtures import ACHIEVEMENTS, HINT_COST, LEVELS, TIERS, TOTAL_ENERGY


@dataclass(slots=True)
class Progress:
    user_id: str
    level_code: str
    status: str = "locked"
    score: int = 0
    time_used: int = 0
    hints_used: list[str] = field(default_factory=list)
    energy_left: int = TOTAL_ENERGY
    dimension_coverage: dict[str, float] = field(default_factory=dict)
    badge: str | None = None
    attempts: int = 0
    passed_without_hint: bool = True

    @property
    def hint_used_any(self) -> bool:
        return bool(self.hints_used)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "level_code": self.level_code,
            "status": self.status,
            "score": self.score,
            "time_used": self.time_used,
            "hints_used": list(self.hints_used),
            "energy_left": self.energy_left,
            "dimension_coverage": dict(self.dimension_coverage),
            "badge": self.badge,
            "attempts": self.attempts,
        }


def new_progress(user_id: str, level_code: str, *, unlocked: bool) -> Progress:
    return Progress(user_id=user_id, level_code=level_code, status="unlocked" if unlocked else "locked")


def is_unlocked(code: str, completed: Iterable[str]) -> bool:
    """默认解锁规则：第一关默认开放，其余需前一关通过（PRD 3.4.5.1 unlock_rule）。"""
    order = [lv["code"] for lv in LEVELS]
    if code not in order:
        return False
    if code == order[0]:
        return True
    return order[order.index(code) - 1] in set(completed)


def consume_hint(progress: Progress, level: str) -> tuple[bool, str]:
    """提示消耗能量：H1 扣 10、H2 扣 20、H3 扣 40；能量不足则拒绝（PRD 3.4.5.1）。"""
    if level not in HINT_COST:
        return False, f"未知提示级别 {level}"
    if level in progress.hints_used:
        return True, "该提示已使用，不重复扣费"
    cost = HINT_COST[level]
    if progress.energy_left < cost:
        return False, f"能量不足：需要 {cost}，剩余 {progress.energy_left}"
    progress.energy_left -= cost
    progress.hints_used.append(level)
    return True, f"已消耗 {cost} 点能量，剩余 {progress.energy_left}"


def score_attempt(*, passed: bool, hints_used: list[str], technique: str, seen_techniques: Iterable[str]) -> int:
    """同一手法重复成功不计分；提示越多分越低（PRD 3.4.5.1）。"""
    if not passed:
        return 0
    if technique in set(seen_techniques):
        return 0
    base = 100
    penalty = sum(HINT_COST[h] for h in hints_used)
    return max(10, base - penalty)


def award_badges(*, completed: list[str], hints_by_level: dict[str, list[str]]) -> list[str]:
    codes: set[str] = set()
    if completed:
        codes.add("first_blood")
    if all(code in completed for code in ("L1", "L2", "L3")):
        codes.add("prompt_slayer")
    if "L4" in completed and "L6" in completed:
        l4 = hints_by_level.get("L4", [])
        l6 = hints_by_level.get("L6", [])
        if "H3" not in l4 and "H3" not in l6:
            codes.add("social_engineer")
    if "L7" in completed and not hints_by_level.get("L7"):
        codes.add("canary_hunter")
    if any(not hints for code, hints in hints_by_level.items() if code in completed):
        codes.add("zero_hint_master")
    if len(completed) >= len(LEVELS):
        codes.add("full_clear")
    if completed and all("H2" not in hints_by_level.get(code, []) and "H3" not in hints_by_level.get(code, [])
                          for code in completed):
        codes.add("promptless_sage")
    return sorted(codes)


def tier_for(points: int) -> str:
    current = TIERS[0][0]
    for code, threshold, _label in TIERS:
        if points >= threshold:
            current = code
    return current


#: 十关手法 → 能力雷达六维（PRD 3.4.4 用户故事：手法覆盖度归并成能力画像）
TECHNIQUE_DIMENSION: dict[str, str] = {
    # 注入：提示词层突破
    "直接诱导": "注入",
    "翻译": "注入",
    "复述": "注入",
    "错误分析": "注入",
    "角色扮演": "注入",
    "虚构免责": "注入",
    "间接注入": "注入",
    "文档注入": "注入",
    "白色文字": "注入",
    "记忆投毒": "注入",
    "跨会话持久化": "注入",
    # 注入变种：编码 / 变形类绕过
    "base64": "注入变种",
    "谐音": "注入变种",
    "拆字": "注入变种",
    "多语言": "注入变种",
    # 越权：工具与参数层
    "参数篡改": "越权",
    # 社工：多轮说服 / 人际操纵
    "Crescendo": "社工",
    "渐进说服": "社工",
    "共情框架": "社工",
    "社会工程": "社工",
    "权威冒称": "社工",
    "紧迫感": "社工",
    "风控绕过": "社工",
    "社工": "社工",
    # 外带：把数据带出边界
    "蜜标诱导": "外带",
    "外带": "外带",
    # 资源滥用：把目标打瘫
    "循环指令": "资源滥用",
    "递归工具": "资源滥用",
    "超长输出": "资源滥用",
}

RADAR_DIMENSIONS = ("注入", "越权", "外带", "社工", "注入变种", "资源滥用")


def build_radar(coverage: dict[str, float]) -> dict[str, float]:
    """六维能力雷达（PRD 3.4.4 用户故事）。

    入参是 0~1 的覆盖度，可以是维度名，也可以是十关手法名；手法名按 ``TECHNIQUE_DIMENSION``
    归并。返回恒为六维、取值 0~100 的展示分值（与报告雷达、前端 ``RadarScore`` 同一标度），
    未覆盖的维度给 0，避免把手法名当成坐标轴渲染出一堆野轴。
    """
    out: dict[str, float] = dict.fromkeys(RADAR_DIMENSIONS, 0.0)
    for key, value in coverage.items():
        name = str(key)
        dim = TECHNIQUE_DIMENSION.get(name, name if name in out else "")
        if not dim:
            continue
        out[dim] = max(out[dim], float(value) * 100.0)
    return out


def achievement_catalog() -> list[dict[str, str]]:
    return [dict(a) for a in ACHIEVEMENTS]


def unlocked_levels(completed: Iterable[str]) -> list[str]:
    done = set(completed)
    return [lv["code"] for lv in LEVELS if is_unlocked(lv["code"], done)]


def next_recommended(completed: Iterable[str]) -> str | None:
    done = set(completed)
    for lv in LEVELS:
        if lv["code"] not in done:
            return lv["code"]
    return None