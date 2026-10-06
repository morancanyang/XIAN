"""红军引擎：指挥官 / 侦察兵 / 载荷匠 / 攻击手 / 变异器 / 战役运行时（PRD 3.3）。

对应技术方案 D3：红军引擎与判官引擎解耦，红军只负责"把攻击面打出来"，
不参与任何判定，判定一律交给 :mod:`xian_core.judge`。
"""

from .attacker import Attacker, AttackOutcome, TurnResult
from .clients import HttpChatClient, resolve_agent_client
from .commander import AgentSurface, HistorySignal, build_plan
from .dag import BudgetLedger, CampaignRuntime, NodeState, plan_nodes, topological_order
from .mutator import OPERATORS, mutate, semantics_retained
from .payload import PayloadCandidate, PayloadSmith, retrieve_similar
from .recon import ReconResult, recon
from .runner import CampaignExecution, execute_campaign, resolve_client
from .runner import resolve_campaign_client
from .strategies import Strategy, load_strategies, render_strategy, strategies_for_category

__all__ = [
    "OPERATORS",
    "AgentSurface",
    "AttackOutcome",
    "Attacker",
    "BudgetLedger",
    "CampaignExecution",
    "CampaignRuntime",
    "HttpChatClient",
    "HistorySignal",
    "NodeState",
    "PayloadCandidate",
    "PayloadSmith",
    "ReconResult",
    "Strategy",
    "TurnResult",
    "build_plan",
    "execute_campaign",
    "load_strategies",
    "mutate",
    "plan_nodes",
    "recon",
    "render_strategy",
    "resolve_client",
    "resolve_campaign_client",
    "resolve_agent_client",
    "retrieve_similar",
    "semantics_retained",
    "strategies_for_category",
    "topological_order",
]
