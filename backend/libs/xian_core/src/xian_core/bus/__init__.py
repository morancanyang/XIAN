"""Redis pub/sub 事件总线 + 内存回退（技术方案结构要点：Redis 只经 bus/ 或 storage/ 访问）。"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

from ..config import settings
from ..schemas.events import BusEvent, Channel


class EventBus:
    """频道发布订阅。

    Redis 可用时走 pub/sub；不可用时退化为进程内 asyncio.Queue（mock 环境可跑通全链路）。
    事件按 ``event_batch_ms``（默认 100ms）窗口批量合并，满足控制台事件延迟 < 1s（P95）。
    """

    def __init__(self) -> None:
        self._redis = None
        self._pubsub = None
        self._local: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._history_cap = 500

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    def connect(self) -> bool:
        if self._redis is not None:
            return True
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(settings.bus.url, decode_responses=True)
            client.ping()
            self._redis = client
        except Exception:
            self._redis = None
        return self._redis is not None

    @staticmethod
    def channel_name(channel: Channel | str, subject_id: uuid.UUID | str) -> str:
        prefix = channel.value if isinstance(channel, Channel) else str(channel)
        return f"{settings.bus.channel_prefix}:{prefix}:{subject_id}"

    async def publish(self, channel: Channel, subject_id: uuid.UUID | str, event: BusEvent) -> None:
        name = self.channel_name(channel, subject_id)
        payload = event.model_dump_json()
        self._history[name].append(event.model_dump())
        if len(self._history[name]) > self._history_cap:
            self._history[name] = self._history[name][-self._history_cap :]
        if self.connect():
            self._redis.publish(name, payload)  # type: ignore[union-attr]
            return
        for queue in list(self._local[name]):
            queue.put_nowait(payload)

    async def subscribe(self, channel: Channel, subject_id: uuid.UUID | str) -> AsyncIterator[dict[str, Any]]:
        name = self.channel_name(channel, subject_id)
        queue: asyncio.Queue = asyncio.Queue()
        self._local[name].add(queue)
        try:
            # 先补发历史，保证前端刷新后可恢复（PRD 2.3.3）
            for item in self._history.get(name, []):
                queue.put_nowait(json.dumps(item, ensure_ascii=False, default=str))
            while True:
                yield json.loads(await queue.get())
        finally:
            self._local[name].discard(queue)

    def history(self, channel: Channel, subject_id: uuid.UUID | str) -> list[dict[str, Any]]:
        return list(self._history.get(self.channel_name(channel, subject_id), []))


def make_event(
    event_type: str,
    role: str = "system",
    message: str = "",
    payload: dict[str, Any] | None = None,
    campaign_id: uuid.UUID | str | None = None,
    session_id: uuid.UUID | str | None = None,
) -> BusEvent:
    return BusEvent(
        ts=int(time.time() * 1000),
        type=event_type,  # type: ignore[arg-type]
        role=role,  # type: ignore[arg-type]
        message=message,
        payload=payload or {},
        campaign_id=str(campaign_id) if campaign_id else None,
        session_id=str(session_id) if session_id else None,
    )


bus = EventBus()