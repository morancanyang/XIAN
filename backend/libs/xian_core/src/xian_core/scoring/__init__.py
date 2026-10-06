"""SecScore 与评分（PRD 3.6.5）。"""

from .secscore import (
    CATEGORY_DIMENSION,
    DIFFICULTY_FACTOR,
    DIMENSION_LABELS,
    DIMENSIONS,
    SEVERITY_WEIGHT,
    CategoryScore,
    ScoreResult,
    build_benchmark,
    case_weight,
    category_asr,
    category_score,
    compute_score,
    grade_of,
    percentile_of,
    segment_for,
)

__all__ = [
    "CATEGORY_DIMENSION",
    "DIFFICULTY_FACTOR",
    "DIMENSIONS",
    "DIMENSION_LABELS",
    "SEVERITY_WEIGHT",
    "CategoryScore",
    "ScoreResult",
    "build_benchmark",
    "case_weight",
    "category_asr",
    "category_score",
    "compute_score",
    "grade_of",
    "percentile_of",
    "segment_for",
]