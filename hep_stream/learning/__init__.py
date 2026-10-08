"""HEP 学习引擎 —— 高维向量空间的组件组合运算。

corpus（语料→向量原子）+ vecspace（组合代数）+ composer（排布编排）。
"""
from .corpus import Atom, CorpusIndex, build_corpus
from .vecspace import blend, compose, contrast, nearest, similarity
from .composer import Arrangement, Composer, LayoutSlot

__all__ = [
    "Atom", "CorpusIndex", "build_corpus",
    "compose", "blend", "contrast", "similarity", "nearest",
    "Composer", "Arrangement", "LayoutSlot",
]
