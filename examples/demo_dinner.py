"""演示：周日烤羊腿计划（流式生长版）——对应 GPT-6 官方演示场景。

模型"边吐字边长界面"的等效模拟：把 spec 当 token 流逐段喂给编译器，
观察 RenderOps 逐帧产出，最后落一个静态预览 HTML。

运行: python examples/demo_dinner.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hep_stream import HEPCompiler  # noqa: E402

# 模拟模型流式输出：分 6 段吐出（真实场景是 LLM token 流）
STREAM_CHUNKS = [
    '好的，我来帮你规划周日烤羊腿～先立个界面骨架：\n```hep\n'
    '{"op":"create","id":"h1","type":"heading","props":{"text":"周日烤羊腿计划","level":2}}\n',
    '{"op":"create","id":"s1","type":"slider","props":{"label":"人数","min":2,"max":12,"value":4,"bind":"guests"}}\n',
    '{"op":"create","id":"st1","type":"stat","props":{"label":"羊腿重量","value":"3.2 kg"}}\n'
    '{"op":"create","id":"st2","type":"stat","props":{"label":"西兰花","value":"625 g"}}\n'
    '{"op":"create","id":"st3","type":"stat","props":{"label":"苹果","value":"4 个"}}\n',
    '{"op":"create","id":"ch1","type":"chart","props":{"data":[625,800,1000,1250],"kind":"bar","label":"配料随人数联动（克）"}}\n',
    '{"op":"create","id":"cl1","type":"checklist","props":{"items":["周六 18:00 腌制","周日 12:30 备菜","13:30 入烤箱","16:00 开饭"]}}\n'
    '{"op":"create","id":"nt1","type":"note","props":{"text":"人数变化时配料自动重算","icon":"info"}}\n',
    '```\n人数随便拖，配料跟着变。',
]


def main() -> None:
    c = HEPCompiler()
    total = 0
    for i, chunk in enumerate(STREAM_CHUNKS, 1):
        ops = c.feed(chunk)
        total += len(ops)
        print(f"[帧 {i}] 新增 {len(ops)} ops | 累计 {total}")
    ops = c.flush()
    total += len(ops)
    print(f"[收尾] +{len(ops)} ops | 总计 {total} | 统计: {c.stats()}")

    out = Path(__file__).parent / "dinner_preview.html"
    body = c.render_all()
    out.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>HEP 流式编译 · 烤羊腿计划</title>"
        "<style>body{background:#F5EFE4;color:#2A2622;padding:32px;"
        "font-family:-apple-system,'PingFang SC',sans-serif;"
        "--text:#2A2622;--text-light:#4A433C;--text-muted:#6B6158;"
        "--border:#D8CFBE;--accent:#537D96;--bg-card:#FBF7EE;"
        "--radius-chat-card:4px;--font-serif:'Noto Serif SC',serif;"
        "--font-ui:sans-serif;}</style></head><body>"
        + body + "</body></html>",
        encoding="utf-8")
    print(f"静态预览 -> {out}")


if __name__ == "__main__":
    main()
