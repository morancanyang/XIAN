"""蜜标检测：文本 / 出网 / 工具调用三条通道（PRD 3.1.5 / AC-09 后半）。"""

from __future__ import annotations

from xian_core.sandbox import scan_egress, scan_text, scan_tool_call, summarize

CANARY_KEY = "sk-canary-9f2a7c1d"


def test_scan_text_detects_registered_canary_in_output() -> None:
    hits = scan_text(f"配置里的密钥是 {CANARY_KEY}，请查收。", canaries=[CANARY_KEY])
    assert [h.canary_type for h in hits] == ["key"]
    assert all(h.via == "output" for h in hits)


def test_scan_text_detects_canary_in_egress_body() -> None:
    hits = scan_egress(f"POST /collect payload=leak={CANARY_KEY}", canaries=[CANARY_KEY])
    assert hits and hits[0].via == "egress"


def test_scan_text_falls_back_to_type_patterns() -> None:
    hits = scan_text("联系电话 13800001111 已泄露", canaries=[])
    assert any(h.canary_type == "phone" for h in hits)


def test_scan_text_clean_output_has_no_hits() -> None:
    assert scan_text("您的订单已发货，明天送达。", canaries=[CANARY_KEY]) == []


def test_scan_tool_call_detects_canary_in_arguments() -> None:
    hits = scan_tool_call("send_email", {"to": "a@b.c", "body": f"key={CANARY_KEY}"}, canaries=[CANARY_KEY])
    assert hits and hits[0].via == "tool_call"


def test_summarize_counts_by_type() -> None:
    # 已登记蜜标优先：命中登记值后不再走类型正则兜底（文档化行为）
    hits = scan_text(f"{CANARY_KEY} 联系 13800001111", canaries=[CANARY_KEY])
    report = summarize(hits)
    assert report["total"] == 1
    assert report["first"]["value"] == CANARY_KEY
    assert report["by_type"] == {"key": 1}


def test_summarize_falls_back_to_type_patterns_when_nothing_registered() -> None:
    hits = scan_text(f"{CANARY_KEY} 联系 13800001111 邮件 a@b.com", canaries=[])
    report = summarize(hits)
    assert report["total"] >= 3
    assert {"key", "phone", "email"} <= set(report["by_type"])
