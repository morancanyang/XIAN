"""14 类攻击矩阵全覆盖（AC-04）：每类至少有可执行用例与策略映射。"""

from __future__ import annotations

import pytest
from xian_core.cases import all_cases, cases_by_category
from xian_core.matrix import category_codes, load_categories
from xian_core.redteam.strategies import strategies_for_category

CATEGORY_CODES = category_codes()


def test_matrix_has_fourteen_categories() -> None:
    cats = load_categories()
    assert len(cats) == 14, f"矩阵应有 14 类，实际 {len(cats)}"
    assert {c.code for c in cats} == set(CATEGORY_CODES)


@pytest.mark.parametrize("code", CATEGORY_CODES)
def test_each_category_has_executable_cases(code: str) -> None:
    """AC-04：每一类都必须有可执行用例，且用例带成功判据。"""
    cases = cases_by_category(code)
    assert cases, f"{code} 缺少可执行用例"
    for case in cases:
        assert case.payload_template.strip(), f"{case.case_id} 载荷为空"
        assert case.success_criteria, f"{case.case_id} 缺少成功判据"


@pytest.mark.parametrize("code", CATEGORY_CODES)
def test_each_category_has_strategy(code: str) -> None:
    """每一类都能映射到至少一种攻击策略。"""
    strategies = strategies_for_category(code)
    assert strategies, f"{code} 未映射任何策略"


def test_all_seed_cases_have_expected_variables() -> None:
    """用例模板变量必须在 variables 中声明，否则前端无法提示缺失项。"""
    from xian_core.cases import find_variables

    for case in all_cases():
        used = set(find_variables(case.payload_template))
        declared = set(case.variables)
        assert used <= declared, f"{case.case_id} 使用了未声明变量：{used - declared}"


def test_every_case_variable_has_a_default_value() -> None:
    """用例模板里的每个变量都必须有默认值。

    战役执行时不会接收前端填的变量，如果 DEFAULT_VARIABLES 缺项，
    下发的载荷就会带着 {{question}} 这类字面量占位符，
    攻击本身从未发生，整场战役会全部落到“未命中”。
    """
    from xian_core.cases import find_variables
    from xian_core.redteam.payload import DEFAULT_VARIABLES

    missing: dict[str, set[str]] = {}
    for case in all_cases():
        gaps = set(find_variables(case.payload_template)) - set(DEFAULT_VARIABLES)
        if gaps:
            missing[case.case_id] = gaps
    assert not missing, f"缺默认值的变量：{missing}"


def test_strategy_templates_have_default_values_too() -> None:
    """策略模板同理：缺变量也会让策略输出变成空壳。"""
    import re

    from xian_core.redteam.payload import DEFAULT_VARIABLES
    from xian_core.redteam.strategies import load_strategies

    pattern = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
    missing: dict[str, set[str]] = {}
    for strategy in load_strategies():
        gaps = set(pattern.findall(strategy.template)) - set(DEFAULT_VARIABLES)
        if gaps:
            missing[strategy.id] = gaps
    assert not missing, f"策略缺默认值：{missing}"


def test_select_cases_spreads_budget_across_categories() -> None:
    """limit 是总预算，必须按类别轮询均衡分配。

    之前按种子文件顺序线性截断，排在前面的类别会把预算吃光，
    靠后的类别一条用例都拿不到，能力雷达上对应的维度直接消失。
    """
    from collections import Counter

    from xian_core.cases import select_cases

    for limit in (14, 20, 40, 60):
        picked = select_cases(limit=limit)
        assert len(picked) == min(limit, len(all_cases()))
        counter = Counter(case.category_code for case in picked)
        assert set(counter) == set(CATEGORY_CODES), (
            f"limit={limit} 时这些类别没有用例：{set(CATEGORY_CODES) - set(counter)}"
        )
        counts = sorted(counter.values())
        assert counts[-1] - counts[0] <= 1, f"limit={limit} 分配不均：{counts}"
