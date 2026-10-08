"""高维向量空间的组合代数 —— 学习引擎的运算层。

四则运算（对"设计原子"的向量坐标做组合）：
    compose(vs, ws)   加权质心（多原子合成一个"意图点"）
    blend(a, b, t)    线性插值（风格渐变："像 A 但偏向 B"）
    contrast(a, b)    向量差（"这个但不要那个"——排斥性指令）
    nearest(vec, k)   最近邻检索（意图点 → 实体原子）
    similarity(a, b)  余弦相似度
"""
from __future__ import annotations

import math
from typing import Sequence

__all__ = ["compose", "blend", "contrast", "similarity", "nearest"]


def _norm(v: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in v)) or 1.0


def similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (_norm(a) * _norm(b))


def compose(vectors: Sequence[Sequence[float]],
            weights: Sequence[float] | None = None) -> list[float]:
    """加权质心合成（L2 归一化）：多个原子的语义意图融合成一个查询点。"""
    if not vectors:
        raise ValueError("compose 需要至少一个向量")
    ws = list(weights) if weights else [1.0] * len(vectors)
    if len(ws) != len(vectors):
        raise ValueError("weights 与 vectors 长度不一致")
    dim = len(vectors[0])
    acc = [0.0] * dim
    for vec, w in zip(vectors, ws):
        for i, x in enumerate(vec):
            acc[i] += x * w
    n = _norm(acc)
    return [x / n for x in acc]


def blend(a: Sequence[float], b: Sequence[float], t: float = 0.5) -> list[float]:
    """线性插值：t=0 全 A，t=1 全 B（风格渐变/保守微调）。"""
    t = max(0.0, min(1.0, t))
    mixed = [(1 - t) * x + t * y for x, y in zip(a, b)]
    n = _norm(mixed)
    return [x / n for x in mixed]


def contrast(target: Sequence[float], unwanted: Sequence[float],
             strength: float = 1.0) -> list[float]:
    """向量差："要 target，但剥掉 unwanted 的味道"（排斥性排布）。"""
    out = [x - strength * y for x, y in zip(target, unwanted)]
    n = _norm(out)
    return [x / n for x in out]


def nearest(query: Sequence[float], atoms: Sequence[tuple[str, Sequence[float]]],
            k: int = 5) -> list[tuple[str, float]]:
    """最近邻：意图点向量 → (atom_ref, 相似度) 列表。"""
    scored = [(ref, similarity(query, vec)) for ref, vec in atoms]
    scored.sort(key=lambda x: -x[1])
    return scored[:k]
