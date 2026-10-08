"""学习引擎实弹：383 原子 → 向量空间排布 → 流式编译。"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hep_stream import HEPCompiler
from hep_stream.learning import Composer, build_corpus

t0 = time.time()
index = build_corpus()
print(f"语料学习: {len(index.atoms)} 原子 / {len(index.sources())} 设计源 / 512 维 | {time.time()-t0:.2f}s")

c = Composer(index)
for query, layout in [("AI 音乐订阅支付结算页", "hero-stats-form"),
                      ("数字生命体监控仪表盘", "dashboard")]:
    arr = c.arrange(query, layout=layout)
    print(f"\n[{query}] 布局={layout}")
    for s in arr.slots:
        print(f"   {s.role:6s} -> {s.ref}  (score {s.score})")
    ops = arr.stream()
    comp = HEPCompiler()
    frames = 0
    for op in ops:
        chunk = "```hep\n" + json.dumps(op, ensure_ascii=False) + "\n```"
        if comp.feed(chunk):
            frames += 1
    comp.flush()
    stat = comp.stats()
    print(f"   流式编译: {len(ops)} spec ops -> {stat['appends']} render ops ({frames} 帧增量)")

refined = c.arrange("音乐人主页", layout="story")
print(f"\n[对比式微调] 原 hero 槽: {refined.slots[0].ref}")
c.refine(refined, towards="pricing table", away="hero banner", slot_index=0)
print(f"             微调后:   {refined.slots[0].ref}  (剥掉 hero 味，向定价表靠拢)")
