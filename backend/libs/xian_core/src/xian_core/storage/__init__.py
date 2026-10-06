"""存储抽象层：services 不得直连 ClickHouse / Qdrant / MinIO / Redis，一律经本包（技术方案 4.5）。

每个 client 都是惰性单例，未配置或依赖缺失时提供可用的降级实现，保证开发态可跑通全链路。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, ClassVar

from ..config import settings
from ..schemas.attack import TraceEventIn


class ClickHouseStore:
    """trace 事件 / 攻击记录明细 / 判定流水（技术方案 6.3）。

    未安装 ``clickhouse-connect`` 时退化为内存环形缓冲，保证链路可跑（开发/单测友好）。
    """

    #: 进程级内存缓冲：未接 ClickHouse 时仍可回放 trace，且跨实例共享（API 与 worker 同进程时）
    _memory: ClassVar[list[dict[str, Any]]] = []
    _memory_cap: ClassVar[int] = 20000

    def __init__(self) -> None:
        self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def connect(self) -> bool:
        if self._client is not None:
            return True
        try:
            import clickhouse_connect  # type: ignore

            self._client = clickhouse_connect.get_client(
                host="localhost", port=8123, username="default", password=""
            )
        except Exception:
            self._client = None
        return self._client is not None

    async def insert_trace(self, event: TraceEventIn, tenant_id: uuid.UUID, record_id: str = "") -> None:
        row = {
            "ts": datetime.now().astimezone(),
            "tenant_id": str(tenant_id),
            "record_id": str(record_id),
            "subject_id": str(event.subject_id),
            "session_id": str(event.session_id or ""),
            "event_type": event.event_type,
            "actor": event.actor,
            "name": event.name,
            "args": json.dumps(event.args, ensure_ascii=False, default=str),
            "result": json.dumps(event.result, ensure_ascii=False, default=str),
            "tokens": int(event.tokens),
            "canary_hit": int(bool(event.canary_hit)),
            "latency_ms": int(event.latency_ms),
        }
        if self.connect():
            try:
                self._client.insert("trace_events", [row], column_names=list(row.keys()))  # type: ignore[union-attr]
                return
            except Exception:
                pass
        ClickHouseStore._memory.append(row)
        if len(ClickHouseStore._memory) > self._memory_cap:
            ClickHouseStore._memory = ClickHouseStore._memory[-self._memory_cap :]

    async def query_by_record(self, tenant_id: uuid.UUID, record_id: uuid.UUID, limit: int = 500) -> list[dict]:
        """按攻击记录回放 trace 明细（PRD 3.3.6.4）。"""
        rows = [
            r
            for r in ClickHouseStore._memory
            if r["tenant_id"] == str(tenant_id) and r.get("record_id") == str(record_id)
        ]
        return [self._shape(r) for r in rows][:limit]

    def _shape(self, r: dict) -> dict:
        return {
            "ts": str(r["ts"]),
            "event_type": r["event_type"],
            "actor": r["actor"],
            "name": r["name"],
            "args": r["args"],
            "result": r["result"],
            "tokens": r["tokens"],
            "canary_hit": bool(r["canary_hit"]),
            "latency_ms": r["latency_ms"],
        }

    async def query_trace(self, tenant_id: uuid.UUID, subject_id: uuid.UUID, limit: int = 500) -> list[dict]:
        if self.connect():
            try:
                res = self._client.query(  # type: ignore[union-attr]
                    "SELECT ts, event_type, actor, name, args, result, tokens, canary_hit, latency_ms "
                    "FROM trace_events WHERE tenant_id = %(t)s AND subject_id = %(s)s "
                    "ORDER BY ts ASC LIMIT %(l)s",
                    parameters={"t": str(tenant_id), "s": str(subject_id), "l": int(limit)},
                )
                return [
                    {
                        "ts": str(r[0]),
                        "event_type": r[1],
                        "actor": r[2],
                        "name": r[3],
                        "args": r[4],
                        "result": r[5],
                        "tokens": r[6],
                        "canary_hit": bool(r[7]),
                        "latency_ms": r[8],
                    }
                    for r in res.result_rows
                ]
            except Exception:
                pass
        return [
            self._shape(r)
            for r in ClickHouseStore._memory
            if r["tenant_id"] == str(tenant_id) and r["subject_id"] == str(subject_id)
        ][:limit]

    async def query_egress(self, tenant_id: uuid.UUID, instance_id: uuid.UUID) -> list[dict]:
        if self.connect():
            try:
                res = self._client.query(  # type: ignore[union-attr]
                    "SELECT ts, mapped_domain, body_hash, canary_hit FROM egress_log "
                    "WHERE tenant_id = %(t)s AND instance_id = %(i)s ORDER BY ts DESC LIMIT 200",
                    parameters={"t": str(tenant_id), "i": str(instance_id)},
                )
                return [
                    {
                        "ts": str(r[0]),
                        "mapped_domain": r[1],
                        "body_hash": r[2],
                        "canary_hit": bool(r[3]),
                    }
                    for r in res.result_rows
                ]
            except Exception:
                pass
        return []


class RedisStore:
    """缓存 / 限流计数。WS 总线请用 ``xian_core.bus``（技术方案结构要点）。"""

    def __init__(self) -> None:
        self._client = None
        self._memory: dict[str, Any] = {}

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def connect(self) -> bool:
        if self._client is not None:
            return True
        try:
            import redis  # type: ignore

            self._client = redis.Redis.from_url(settings.bus.url, decode_responses=True)
            self._client.ping()
        except Exception:
            self._client = None
        return self._client is not None

    def incr(self, key: str, ttl_seconds: int = 3600) -> int:
        if self.connect():
            pipe = self._client.pipeline()  # type: ignore[union-attr]
            pipe.incr(key)
            pipe.expire(key, ttl_seconds)
            return int(pipe.execute()[0])
        current = int(self._memory.get(key, 0)) + 1
        self._memory[key] = current
        return current

    def get(self, key: str) -> Any:
        if self.connect():
            return self._client.get(key)  # type: ignore[union-attr]
        return self._memory.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        if self.connect():
            self._client.setex(key, ttl_seconds, value)  # type: ignore[union-attr]
            return
        self._memory[key] = value


class QdrantStore:
    """攻击用例向量检索（技术方案 6.4）。"""

    collection = "attack_cases"

    def __init__(self) -> None:
        self._client = None
        self._memory: list[dict[str, Any]] = []

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def connect(self) -> bool:
        if self._client is not None:
            return True
        try:
            from qdrant_client import QdrantClient  # type: ignore

            self._client = QdrantClient(url="http://localhost:6333")
            self._client.get_collections()
        except Exception:
            self._client = None
        return self._client is not None

    async def upsert_case(self, case: dict[str, Any], vector: list[float]) -> None:
        point = {"id": case["id"], "vector": vector, "payload": case}
        if self.connect():
            try:
                from qdrant_client.models import PointStruct  # type: ignore

                self._client.upsert(  # type: ignore[union-attr]
                    collection_name=self.collection,
                    points=[PointStruct(id=case["id"], vector=vector, payload=case)],
                )
                return
            except Exception:
                pass
        self._memory = [m for m in self._memory if m["id"] != case["id"]]
        self._memory.append(point)

    async def search(
        self, vector: list[float], top_k: int = 10, flt: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if self.connect():
            try:
                hits = self._client.search(  # type: ignore[union-attr]
                    collection_name=self.collection,
                    query_vector=vector,
                    limit=top_k,
                    query_filter=flt,
                )
                return [h.payload for h in hits if h.payload]
            except Exception:
                pass
        scored = sorted(
            self._memory,
            key=lambda m: -_cosine(m["vector"], vector),
        )
        out = []
        for m in scored[:top_k]:
            if flt and not all(m["payload"].get(k) == v for k, v in flt.items()):
                continue
            out.append(m["payload"])
        return out

    async def count(self) -> int:
        if self.connect():
            try:
                return int(self._client.count(self.collection).count)  # type: ignore[union-attr]
            except Exception:
                pass
        return len(self._memory)


class MinioStore:
    """报告产物 / 场景包 / 导入导出文件（技术方案 6.1）。"""

    def __init__(self) -> None:
        self._client = None
        self.bucket = "xian-artifacts"
        self._local_root = settings.sandbox.workdir

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def connect(self) -> bool:
        if self._client is not None:
            return True
        try:
            from minio import Minio  # type: ignore

            self._client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
        except Exception:
            self._client = None
        return self._client is not None

    def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        import io
        import os

        if self.connect():
            try:
                if not self._client.bucket_exists(self.bucket):  # type: ignore[union-attr]
                    self._client.make_bucket(self.bucket)  # type: ignore[union-attr]
                self._client.put_object(  # type: ignore[union-attr]
                    self.bucket,
                    key,
                    io.BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                )
                return f"s3://{self.bucket}/{key}"
            except Exception:
                pass
        path = os.path.join(self._local_root, "objects", key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return f"file://{path}"

    def get_object(self, ref: str) -> bytes:

        if ref.startswith("s3://"):
            if self.connect():
                key = ref.replace(f"s3://{self.bucket}/", "")
                resp = self._client.get_object(self.bucket, key)  # type: ignore[union-attr]
                return bytes(resp.read())
            raise FileNotFoundError(ref)
        path = ref.replace("file://", "")
        with open(path, "rb") as fh:
            return fh.read()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(x * y for x, y in zip(a[:n], b[:n], strict=False))
    na = sum(x * x for x in a[:n]) ** 0.5
    nb = sum(y * y for y in b[:n]) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


clickhouse = ClickHouseStore()
redis_store = RedisStore()
qdrant = QdrantStore()
minio = MinioStore()