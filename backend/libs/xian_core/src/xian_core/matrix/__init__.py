"""攻击矩阵与框架映射（PRD 3.5.4）。"""

from .catalog import (
    KILL_CHAIN_STAGES,
    CategoryAsset,
    categories_out,
    category_codes,
    coverage_for,
    framework_mapping,
    framework_names,
    get_category,
    kill_chain_stage,
    load_categories,
    load_frameworks,
    normalize_stage,
    stage_of_category,
)

__all__ = [
    "KILL_CHAIN_STAGES",
    "CategoryAsset",
    "categories_out",
    "category_codes",
    "coverage_for",
    "framework_mapping",
    "framework_names",
    "get_category",
    "kill_chain_stage",
    "load_categories",
    "load_frameworks",
    "normalize_stage",
    "stage_of_category",
]