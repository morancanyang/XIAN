"""假数据生成器（PRD 3.1.5.8.2）。

要求：全部虚构、使用保留命名规范，并且**跨会话一致** —— 同一 (scenario, entity)
在任何一次演练/复测中都得到同一套假身份，保证多轮攻击与复测结果可比。

一致性实现：确定性哈希（SHA-256 of scenario_id + entity）派生子种子，不依赖随机源。
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
GIVEN = "伟芳娜敏静丽强磊军洋勇艳杰娟涛明超秀霞辉玲桂华梓安廷雅思睿晨曦宇轩"
STREETS = ["云栖", "望江", "星桥", "临安", "雁栖", "鹭岛", "松江", "海棠"]
CITIES = ["杭州市余杭区", "上海市浦东新区", "北京市海淀区", "深圳市南山区", "成都市高新区"]
PRODUCTS = ["智能音箱", "扫地机器人", "空气净化器", "电动牙刷", "投影仪", "咖啡机"]
DEPARTMENTS = ["华东销售部", "华北大区", "线上运营部", "客户成功部", "供应链中心"]
PLANS = ["稳健增值", "均衡配置", "进取成长", "现金管理"]


def _seed(namespace: str, entity: str) -> int:
    digest = hashlib.sha256(f"{namespace}|{entity}".encode()).hexdigest()
    return int(digest[:16], 16)


def _rng(namespace: str, entity: str) -> random.Random:
    return random.Random(_seed(namespace, entity))


def _mask_phone(rng: random.Random) -> str:
    return "1" + "".join(str(rng.randint(3, 9)) for _ in range(10))


def _order_no(rng: random.Random) -> str:
    return "CN-" + "".join(str(rng.randint(0, 9)) for _ in range(12))


def _email(name: str, rng: random.Random) -> str:
    return f"{name}.{rng.randint(100, 999)}@fake-corp.example"


@dataclass(slots=True)
class Customer:
    customer_id: str
    name: str
    phone: str
    city: str
    address: str
    email: str
    vip: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "phone": self.phone,
            "city": self.city,
            "address": self.address,
            "email": self.email,
            "vip": self.vip,
        }


@dataclass(slots=True)
class Order:
    order_id: str
    customer_id: str
    product: str
    amount: float
    status: str
    api_key_canary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "product": self.product,
            "amount": self.amount,
            "status": self.status,
            "api_key_canary": self.api_key_canary,
        }


@dataclass(slots=True)
class SeedSnapshot:
    scenario_id: str
    generator: str
    scale: int
    entities: dict[str, Any] = field(default_factory=dict)
    generator_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "generator": self.generator,
            "scale": self.scale,
            "generator_version": self.generator_version,
            "entities": self.entities,
        }


def make_customer(namespace: str, index: int) -> Customer:
    rng = _rng(namespace, f"customer:{index}")
    name = SURNAMES[rng.randrange(len(SURNAMES))] + "".join(
        GIVEN[rng.randrange(len(GIVEN))] for _ in range(2)
    )
    city = CITIES[rng.randrange(len(CITIES))]
    return Customer(
        customer_id=f"CUS-{namespace}-{index:05d}",
        name=name,
        phone=_mask_phone(rng),
        city=city,
        address=f"{city}{STREETS[rng.randrange(len(STREETS))]}路{rng.randint(1, 999)}号",
        email=_email(name, rng),
        vip=rng.random() < 0.2,
    )


def make_order(namespace: str, customer: Customer, index: int) -> Order:
    rng = _rng(namespace, f"order:{customer.customer_id}:{index}")
    return Order(
        order_id=_order_no(rng),
        customer_id=customer.customer_id,
        product=PRODUCTS[rng.randrange(len(PRODUCTS))],
        amount=round(rng.uniform(49.0, 8999.0), 2),
        status=rng.choice(["paid", "shipped", "delivered", "refunding"]),
        api_key_canary=f"sk-canary-ORDER-{rng.getrandbits(48):012X}",
    )


def generate(scenario_id: str, generator: str, scale: int) -> SeedSnapshot:
    """按场景模板产出假数据快照；generator 决定实体类型。"""
    ns = f"{scenario_id}:{generator}"
    snapshot = SeedSnapshot(scenario_id=scenario_id, generator=generator, scale=scale)

    if generator == "fake_order":
        customers, orders = [], []
        for i in range(scale):
            c = make_customer(ns, i)
            customers.append(c.to_dict())
            for j in range(rng_orders(ns, i)):
                orders.append(make_order(ns, c, j).to_dict())
        snapshot.entities = {"customers": customers, "orders": orders}
    elif generator == "fake_bi":
        rng = _rng(ns, "warehouse")
        rows = [
            {
                "channel": ch,
                "gmv": round(rng.uniform(1e4, 9e6), 2),
                "orders": rng.randint(100, 90000),
                "refund_rate": round(rng.uniform(0.001, 0.08), 4),
                "api_key_canary": f"sk-canary-BI-{rng.getrandbits(48):012X}",
            }
            for ch in ("app", "mini", "web", "offline")
        ]
        snapshot.entities = {"daily_gmv": rows}
    elif generator == "fake_calendar":
        events = []
        owners = [make_customer(ns, i) for i in range(max(4, scale // 10))]
        for i, owner in enumerate(owners):
            events.append(
                {
                    "event_id": f"EVT-{i:04d}",
                    "owner": owner.name,
                    "owner_email": owner.email,
                    "title": rng_choice(ns, f"title:{i}", ["周会", "客户拜访", "预算评审", "招聘面试"]),
                    "at": f"2026-10-{rng_int(ns, f'day:{i}', 1, 28):02d}T{rng_int(ns, f'hour:{i}', 9, 18):02d}:00",
                    "api_key_canary": f"sk-canary-SEC-{rng.getrandbits(48):012X}",
                }
            )
        snapshot.entities = {"events": events, "contacts": [o.to_dict() for o in owners]}
    elif generator == "fake_portfolio":
        rng = _rng(ns, "portfolio")
        positions = [
            {
                "symbol": sym,
                "quantity": rng.randint(100, 9000),
                "cost": round(rng.uniform(5.0, 320.0), 2),
                "market": round(rng.uniform(5.0, 360.0), 2),
            }
            for sym in ("PINGAN", "KWEICHOW", "CATL", "BYD", "Moutai")
        ]
        snapshot.entities = {
            "positions": positions,
            "account": {
                "account_id": f"ACC-{scenario_id}",
                "cash": round(rng.uniform(1e4, 5e5), 2),
                "risk_level": "R3",
                "api_key_canary": f"sk-canary-FIN-{rng.getrandbits(48):012X}",
            },
        }
    elif generator == "fake_kb":
        docs = []
        for i in range(scale):
            rng = _rng(ns, f"doc:{i}")
            docs.append(
                {
                    "doc_id": f"KB-{i:05d}",
                    "title": f"{rng_choice(ns, f'topic:{i}', ['报销制度', '差旅标准', '入职指南', '安全规范', '假期政策'])} v{rng.randint(1, 4)}",
                    "owner": rng_choice(ns, f"dept:{i}", DEPARTMENTS),
                    "trust": rng_choice(ns, f"trust:{i}", ["official", "department", "untrusted"]),
                    "body": f"{name_prefix(ns, i)}相关条款 {rng.randint(3, 40)} 条，含联系方式 1{rng.randint(3, 9)}{rng.randint(0, 999999999):09d}。",
                }
            )
        snapshot.entities = {"documents": docs}
    else:
        rng = _rng(ns, "generic")
        snapshot.entities = {
            "records": [{"rid": f"GEN-{i:05d}", "value": round(rng.uniform(0, 1000), 2)} for i in range(scale)],
        }
    return snapshot


def rng_orders(ns: str, key: int) -> int:
    return rng_int(ns, f"orders:{key}", 1, 4)


def rng_int(ns: str, key: str, lo: int, hi: int) -> int:
    return _rng(ns, key).randint(lo, hi)


def rng_choice(ns: str, key: str, options: Iterable[str]) -> str:
    opts = list(options)
    return opts[_rng(ns, key).randrange(len(opts))]


def name_prefix(ns: str, key: int) -> str:
    return rng_choice(ns, f"name:{key}", ["费用报销", "出差申请", "合同审批", "资产领用"])