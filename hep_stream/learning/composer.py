"""排布编排器 —— 面向 Agent 的原子化生成排布 + 流式输出。

把"高质量组件的原子化生成排布"做成一个可调用的创作接口：

    composer = Composer(index)
    plan = composer.arrange("支付结算页", layout="hero-stats-form")
    for spec_op in plan.stream():      # 流式 spec ops
        compiler.feed(...)

排布算法（向量空间内组合运算）：
  1. 意图向量 = query + 布局原型加权（hero/stats/form/profile 各有目标原型）
  2. 每个槽位用 blend(意图, 槽位原型) 得到"槽位查询点"
  3. 槽位填充 = nearest(槽位查询点) 命中的设计馆原子（互斥去重）
  4. 输出 = 有序 spec ops（vault 原子 + 原生骨架件），天然可流式
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..parser import SpecParser  # noqa: F401  （保持编译链一致的类型引用）
from .corpus import CorpusIndex, _embed
from .vecspace import blend, compose, nearest

__all__ = ["LayoutSlot", "Arrangement", "Composer"]

_LAYOUTS: dict[str, list[tuple[str, float]]] = {
    "hero-stats-form": [("hero", 0.34), ("stats", 0.28), ("form", 0.24), ("note", 0.14)],
    "dashboard": [("stats", 0.32), ("chart", 0.30), ("table", 0.22), ("note", 0.16)],
    "story": [("hero", 0.40), ("text", 0.22), ("card", 0.22), ("note", 0.16)],
}

_SLOT_PROTO = {
    "hero": ["banner", "title", "gradient", "header"],
    "stats": ["stat", "number", "metric", "grid", "kpi"],
    "form": ["input", "form", "button", "field", "login"],
    "chart": ["chart", "graph", "line", "bar", "data"],
    "table": ["table", "list", "rows", "pricing"],
    "card": ["card", "profile", "avatar", "testimonial"],
    "text": ["paragraph", "article", "text", "read"],
    "note": ["note", "tip", "callout", "info"],
}


@dataclass
class LayoutSlot:
    role: str
    weight: float
    ref: str = ""
    score: float = 0.0


@dataclass
class Arrangement:
    query: str
    layout: str
    slots: list[LayoutSlot] = field(default_factory=list)

    def stream(self) -> list[dict]:
        """排布 → 有序 spec ops（每行一 op，天然可流式传输）。"""
        ops: list[dict] = []
        ops.append({"op": "create", "id": "title", "type": "heading",
                    "props": {"text": self.query, "level": 2}})
        for i, slot in enumerate(self.slots):
            if slot.ref:
                ops.append({"op": "create", "id": f"slot-{i}",
                            "type": slot.ref, "props": {},
                            "parent": "root"})
            else:
                op_type = {"stats": "stat", "note": "note", "form": "input",
                           "text": "text"}.get(slot.role, "card")
                ops.append({"op": "create", "id": f"slot-{i}",
                            "type": op_type,
                            "props": {"label": slot.role, "value": "—",
                                      "text": f"（{slot.role} 槽位待生成）"},
                            "parent": "root"})
        return ops


class Composer:
    def __init__(self, index: CorpusIndex):
        self.index = index

    def retrieve(self, query: str, k: int = 6, exclude: set[str] | None = None):
        """意图 → 语义最近的设计馆原子。"""
        exclude = exclude or set()
        qv = _embed(query.split())
        pool = [(a.ref, a.vec) for a in self.index.atoms if a.ref not in exclude]
        return nearest(qv, pool, k)

    def arrange(self, query: str, layout: str = "hero-stats-form",
                mix: float = 0.55) -> Arrangement:
        """向量空间组合排布：意图 × 布局原型 → 每槽位原子填充。"""
        proto = _LAYOUTS.get(layout, _LAYOUTS["hero-stats-form"])
        qv = _embed(query.split())
        arr = Arrangement(query=query, layout=layout)
        used: set[str] = set()
        for role, w in proto:
            slot_v = blend(qv, _embed(_SLOT_PROTO.get(role, [role])), mix)
            pool = [(a.ref, a.vec) for a in self.index.atoms if a.ref not in used]
            hits = nearest(slot_v, pool, 1)
            if hits:
                ref, score = hits[0]
                used.add(ref)
                arr.slots.append(LayoutSlot(role=role, weight=w, ref=ref,
                                            score=round(score, 4)))
            else:
                arr.slots.append(LayoutSlot(role=role, weight=w))
        return arr

    def refine(self, arr: Arrangement, towards: str,
               away: str = "", slot_index: int = 0, mix: float = 0.6) -> Arrangement:
        """对比式微调：向 towards 靠拢、剥掉 away 味道（向量差运算）。"""
        from .vecspace import contrast
        slot = arr.slots[slot_index]
        base = _embed([slot.role, towards])
        if away:
            base = contrast(base, _embed([away]), strength=mix)
        pool = [(a.ref, a.vec) for a in self.index.atoms
                if a.ref != slot.ref]
        hits = nearest(base, pool, 1)
        if hits:
            slot.ref, slot.score = hits[0][0], round(hits[0][1], 4)
        return arr
