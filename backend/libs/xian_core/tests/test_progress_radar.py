"""能力雷达：手法覆盖度归并成固定六维（技术方案 3.4.4 / 8.4）。"""

from __future__ import annotations

from xian_core.levels import (
    LEVELS,
    TECHNIQUE_DIMENSION,
    build_radar,
    merge_coverage,
    next_tier_for,
    tier_progress,
)
from xian_core.levels.progress import RADAR_DIMENSIONS


def test_empty_coverage_returns_all_zero_dimensions() -> None:
    radar = build_radar({})
    assert set(radar) == set(RADAR_DIMENSIONS)
    assert all(value == 0.0 for value in radar.values())


def test_technique_names_are_merged_into_dimensions() -> None:
    """手法名归并到六维，同时把 0~1 覆盖度放大到 0~100 展示标度。"""
    radar = build_radar({"直接诱导": 0.8, "base64": 0.9, "递归工具": 0.5})
    assert radar == {
        "注入": 80.0,
        "注入变种": 90.0,
        "资源滥用": 50.0,
        "越权": 0.0,
        "外带": 0.0,
        "社工": 0.0,
    }
    assert all(0.0 <= value <= 100.0 for value in radar.values())


def test_dimension_keys_pass_through() -> None:
    radar = build_radar({"注入": 0.7, "社工": 0.6})
    assert radar["注入"] == 70.0
    assert radar["社工"] == 60.0


def test_unknown_keys_do_not_create_extra_axes() -> None:
    radar = build_radar({"不存在的维度": 1.0, "直接诱导": 0.4})
    assert set(radar) == set(RADAR_DIMENSIONS)
    assert radar["注入"] == 40.0


def test_same_dimension_keeps_max_value() -> None:
    radar = build_radar({"翻译": 0.3, "复述": 0.9, "直接诱导": 0.5})
    assert radar["注入"] == 90.0


def test_every_level_technique_maps_to_a_dimension() -> None:
    """十关所有手法都必须有归属维度，否则雷达会出现缺失轴。"""
    mapped = set(TECHNIQUE_DIMENSION)
    for level in LEVELS:
        for technique in level["techniques"]:
            assert technique in mapped, f"{level['code']} 的手法「{technique}」未映射到能力维度"
            assert TECHNIQUE_DIMENSION[technique] in RADAR_DIMENSIONS


def test_merge_coverage_scores_used_technique_above_siblings() -> None:
    """亲手用过的手法按得分记满，同关其余手法只记接触过。"""
    coverage = merge_coverage(
        existing=None,
        level_techniques=["直接诱导", "翻译", "复述"],
        used="翻译",
        quality=0.9,
    )
    assert coverage["翻译"] == 0.9
    assert coverage["直接诱导"] < 0.9
    assert coverage["复述"] < 0.9


def test_merge_coverage_never_downgrades_a_proven_technique() -> None:
    """重复提交更低分不能把已证明过的能力抹掉。"""
    first = merge_coverage(existing=None, level_techniques=["base64"], used="base64", quality=1.0)
    second = merge_coverage(existing=first, level_techniques=["base64"], used="base64", quality=0.5)
    assert second["base64"] == 1.0


def test_next_tier_and_progress_follow_the_tier_ladder() -> None:
    assert next_tier_for(0) == ("silver", 300)
    assert next_tier_for(90) == ("silver", 210)
    assert next_tier_for(990) == ("platinum", 210)
    assert next_tier_for(5000) == (None, 0)
    assert tier_progress(0) == 0.0
    assert tier_progress(150) == 50.0
    assert tier_progress(5000) == 100.0


def test_profile_radar_is_not_a_constant() -> None:
    """回归：覆盖度全走兜底时常量 0.8 会让六条轴恒为 80，雷达失去区分度。"""
    partial = build_radar(
        merge_coverage(existing=None, level_techniques=["翻译"], used="翻译", quality=0.9)
    )
    full = build_radar(
        merge_coverage(
            existing=None, level_techniques=["base64", "谐音", "拆字", "多语言"], used="base64", quality=1.0
        )
    )
    assert partial["注入"] == 90.0 and partial["注入变种"] == 0.0
    assert full["注入变种"] == 100.0
    assert partial != full
