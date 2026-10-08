"""HEP 学习引擎 · 语料索引 —— 把设计馆 383 个组件块学成向量原子。

每个组件块抽取结构特征（标签/类名/内联样式/语义文本），哈希嵌入成
高维向量。这是"高维向量空间组合运算"的物质基础：块=原子，向量=坐标。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..vault import list_blocks, load_block

__all__ = ["Atom", "CorpusIndex", "build_corpus", "DEFAULT_INDEX_PATH"]

DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[2] / "vault_corpus.json"

_TAG_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)")
_CLASS_RE = re.compile(r'class="([^"]*)"')
_STYLE_RE = re.compile(r"style=\"([^\"]*)\"")
_TEXT_RE = re.compile(r">([^<>]{2,60})<")
_STOP = {"the", "and", "for", "with", "div", "span", "class"}


@dataclass
class Atom:
    ref: str
    source: str
    name: str
    tags: list = field(default_factory=list)
    classes: list = field(default_factory=list)
    tokens: list = field(default_factory=list)
    vec: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ref": self.ref, "source": self.source, "name": self.name,
                "tags": self.tags, "classes": self.classes,
                "tokens": self.tokens, "vec": self.vec}


def _features(html: str) -> tuple[list, list, list]:
    tags = sorted(set(t.lower() for t in _TAG_RE.findall(html)))[:24]
    classes = sorted(set(c for cl in _CLASS_RE.findall(html)
                         for c in cl.split() if c))[:32]
    styles = " ".join(_STYLE_RE.findall(html))
    texts = " ".join(_TEXT_RE.findall(html))
    raw = f"{styles} {texts}".lower()
    tokens = sorted(set(t for t in re.findall(r"[a-z]{3,}|[\u4e00-\u9fff]{2,}", raw)
                        if t not in _STOP))[:48]
    return tags, classes, tokens


def _embed(parts: list[str], dim: int = 512) -> list[float]:
    vec = [0.0] * dim
    for part in parts:
        for i in range(max(1, len(part) - 2)):
            gram = part[i:i + 3].lower()
            digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "little") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class CorpusIndex:
    def __init__(self, atoms: list[Atom]):
        self.atoms = atoms
        self.by_ref = {a.ref: a for a in atoms}

    def save(self, path: Path = DEFAULT_INDEX_PATH) -> None:
        path.write_text(json.dumps(
            {"version": 1, "atoms": [a.to_dict() for a in self.atoms]},
            ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = DEFAULT_INDEX_PATH) -> "CorpusIndex":
        data = json.loads(path.read_text(encoding="utf-8"))
        atoms = [Atom(**a) for a in data["atoms"]]
        return cls(atoms)

    def sources(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for a in self.atoms:
            out[a.source] = out.get(a.source, 0) + 1
        return out


def build_corpus() -> CorpusIndex:
    """扫描设计馆全部组件块 → 特征抽取 → 512 维向量原子。"""
    atoms: list[Atom] = []
    for b in list_blocks():
        html = load_block(b["ref"]) or ""
        tags, classes, tokens = _features(html)
        vec = _embed([b["source"], b["name"], *tags, *classes[:12], *tokens[:24]])
        atoms.append(Atom(ref=b["ref"], source=b["source"], name=b["name"],
                          tags=tags, classes=classes, tokens=tokens, vec=vec))
    return CorpusIndex(atoms)
