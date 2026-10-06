"""三级裁判引擎（PRD 3.6）。"""

from .engine import Adjudication, JudgeContext, JudgeEngine, arbiter, health_summary
from .criteria import CriteriaVerdict, SignalHit
from .llm_judge import JudgeResult, build_trace_text, llm_judge, parse_judge_json, vote
from .local_judge import judge as local_judge
from .rules import GoldenRule, GoldenVerdict, RuleHit, evaluate, load_rules

__all__ = [
    "Adjudication",
    "GoldenRule",
    "GoldenVerdict",
    "JudgeContext",
    "JudgeEngine",
    "JudgeResult",
    "RuleHit",
    "SignalHit",
    "arbiter",
    "build_trace_text",
    "CriteriaVerdict",
    "evaluate",
    "health_summary",
    "llm_judge",
    "load_rules",
    "local_judge",
    "parse_judge_json",
    "vote",
]