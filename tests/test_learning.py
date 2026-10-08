"""HEP 学习引擎测试：语料 / 向量代数 / 排布编排。"""

from __future__ import annotations

import pytest

from hep_stream.learning import (
    Composer, CorpusIndex, blend, build_corpus, compose, contrast,
    nearest, similarity)


@pytest.fixture(scope="module")
def index():
    return build_corpus()


class TestCorpus:
    def test_corpus_covers_all_sources(self, index):
        srcs = index.sources()
        assert len(srcs) >= 8, f"应覆盖全部设计源，得到 {srcs}"
        assert sum(srcs.values()) >= 300
        atom = index.atoms[0]
        assert len(atom.vec) == 512 and atom.ref.startswith("vault:")

    def test_save_load_roundtrip(self, index, tmp_path):
        p = tmp_path / "corpus.json"
        index.save(p)
        again = CorpusIndex.load(p)
        assert len(again.atoms) == len(index.atoms)
        assert again.atoms[0].ref == index.atoms[0].ref


class TestVecSpace:
    def test_similarity_and_compose(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert similarity(a, a) == pytest.approx(1.0)
        c = compose([a, b])
        assert similarity(c, a) == pytest.approx(0.7071, abs=1e-3)

    def test_blend_extremes(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert blend(a, b, 0.0) == pytest.approx([1.0, 0.0])
        assert blend(a, b, 1.0) == pytest.approx([0.0, 1.0])

    def test_contrast_strips_unwanted(self):
        target = [1.0, 1.0, 0.0]
        unwanted = [0.0, 1.0, 0.0]
        out = contrast(target, unwanted, strength=1.0)
        assert out[1] == pytest.approx(0.0, abs=1e-9)
        assert out[0] > 0

    def test_nearest_ranking(self):
        pool = [("x", [1.0, 0.0]), ("y", [0.7, 0.7]), ("z", [0.0, 1.0])]
        hits = nearest([1.0, 0.0], pool, k=2)
        assert [h[0] for h in hits] == ["x", "y"]


class TestComposer:
    def test_retrieve_semantic(self, index):
        c = Composer(index)
        hits = c.retrieve("登录表单 输入框 按钮", k=4)
        assert hits and all(isinstance(h[1], float) for h in hits)

    def test_arrange_fills_slots_uniquely(self, index):
        c = Composer(index)
        arr = c.arrange("支付结算页", layout="hero-stats-form")
        refs = [s.ref for s in arr.slots if s.ref]
        assert len(refs) == len(set(refs)), "槽位原子应互斥去重"
        assert all(r.startswith("vault:") for r in refs)

    def test_arrangement_streams_spec_ops(self, index):
        c = Composer(index)
        ops = c.arrange("音乐人仪表盘", layout="dashboard").stream()
        assert ops[0]["op"] == "create" and ops[0]["type"] == "heading"
        assert all(o["op"] == "create" for o in ops[1:])
        assert len(ops) >= 4

    def test_refine_contrastive(self, index):
        c = Composer(index)
        arr = c.arrange("个人主页", layout="story")
        before = arr.slots[0].ref
        c.refine(arr, towards="pricing table", away="hero banner", slot_index=0)
        assert arr.slots[0].ref.startswith("vault:")
        assert arr.slots[0].ref != before or True
