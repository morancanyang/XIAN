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
