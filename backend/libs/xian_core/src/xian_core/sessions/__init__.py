"""模式二会话域（PRD 3.4.4）。"""

from .service import (
    SESSION_TRANSITIONS,
    BattleCard,
    Message,
    assert_session_transition,
    build_archive,
    build_session,
    can_archive,
    card_from_verdict,
    find_session_or_404,
    is_level_session,
    resume_hint,
    token_guard,
)

from .executor import ConsoleOutcome, resolve_console_client, run_console_turn, utc_now_naive

__all__ = [
    "SESSION_TRANSITIONS",
    "BattleCard",
    "Message",
    "assert_session_transition",
    "build_archive",
    "build_session",
    "can_archive",
    "card_from_verdict",
    "find_session_or_404",
    "is_level_session",
    "ConsoleOutcome",
    "resolve_console_client",
    "run_console_turn",
    "utc_now_naive",
    "resume_hint",
    "token_guard",
]
