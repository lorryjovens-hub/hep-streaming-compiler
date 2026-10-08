"""HEP 流式编译器测试：增量性 / 容错 / 审美 lint / 组件编译。"""

from __future__ import annotations

import pytest

from hep_stream import HEPCompiler, compile_component, lint_spec


SPEC = '''对话文本开头
```hep
{"op":"create","id":"t1","type":"heading","props":{"text":"周日烤羊腿","level":2}}
{"op":"create","id":"s1","type":"slider","props":{"label":"人数","min":2,"max":12,"value":4,"bind":"guests"}}
{"op":"create","id":"st1","type":"stat","props":{"label":"羊腿重量","value":"3.2kg"}}
```hep
收尾文本
'''


class TestStreaming:
    def test_ops_emitted_incrementally(self):
        c = HEPCompiler()
        mid_ops = []
        for i in range(0, len(SPEC), 7):   # 逐 7 字符喂，模拟 token 流
            mid_ops.append(len(c.feed(SPEC[i:i + 7])))
        assert any(n > 0 for n in mid_ops[:-1]), "应在流结束前就产出 op（边吐边长）"
        c.flush()
        assert c.stats()["appends"] == 3

    def test_order_preserved(self):
        c = HEPCompiler()
        ops = c.feed(SPEC) + c.flush()
        ids = [o["id"] for o in ops if o["op"] == "append"]
        assert ids == ["t1", "s1", "st1"]

    def test_partial_line_buffered_then_flushed(self):
        c = HEPCompiler()
        c.feed('```hep\n{"op":"create","id":"x","type":"text","props":{"text":"hi"}}')
        assert c.stats()["appends"] == 0      # 无换行，行未完成
        ops = c.flush()
        assert ops and ops[0]["id"] == "x"    # flush 兜底解析

    def test_bad_line_recorded_not_silent(self):
        c = HEPCompiler()
        ops = c.feed('```hep\n{"op":"create","id":"a","type":"text","props":{"text":"ok"}}\n{{{{坏行\n```')
        assert any(o.get("id") == "a" for o in ops)
        assert c._parser.bad_lines and "坏行" in c._parser.bad_lines[0]

    def test_patch_and_remove(self):
        c = HEPCompiler()
        ops = c.feed('```hep\n{"op":"patch","id":"a","props":{"value":6}}\n'
                     '{"op":"remove","id":"b"}\n```') + c.flush()
        kinds = [o["op"] for o in ops]
        assert kinds == ["patch", "remove"]


class TestLint:
    def test_emoji_icon_is_error(self):
        issues = lint_spec({"op": "create", "id": "i", "type": "note",
                            "props": {"text": "hi", "icon": "🔥"}})
        assert any(i["level"] == "error" and i["rule"] == "L1" for i in issues)

    def test_button_requires_label(self):
        issues = lint_spec({"op": "create", "id": "b", "type": "button",
                            "props": {"action": "go"}})
        assert any(i["rule"] == "L5" and i["level"] == "error" for i in issues)

    def test_alert_and_hex_flags(self):
        issues = lint_spec({"op": "create", "id": "n", "type": "note",
                            "props": {"text": "alert('x') #ff0000"}})
        rules = {i["rule"] for i in issues}
        assert "L3" in rules and "L4" in rules

    def test_strict_blocks_emit(self):
        c = HEPCompiler(strict=True)
        ops = c.feed('```hep\n{"op":"create","id":"b","type":"button","props":{"action":"x"}}\n```')
        assert not any(o["op"] == "append" for o in ops)
        assert c.rejected

    def test_lint_ops_emitted(self):
        c = HEPCompiler()
        ops = c.feed('```hep\n{"op":"create","id":"n","type":"note","props":{"text":"hi","icon":"🔥"}}\n```')
        lint_ops = [o for o in ops if o["op"] == "lint"]
        assert lint_ops and lint_ops[0]["issues"]


class TestComponents:
    def test_unknown_type_rejected(self):
        c = HEPCompiler()
        c.feed('```hep\n{"op":"create","id":"z","type":"warp-drive","props":{}}\n```')
        assert c.rejected and "未知组件类型" in c.rejected[0]["error"]

    def test_missing_required_prop_rejected(self):
        c = HEPCompiler()
        c.feed('```hep\n{"op":"create","id":"h","type":"heading","props":{}}\n```')
        assert c.rejected

    def test_chart_renders_both_kinds(self):
        bar = compile_component({"type": "chart", "id": "c1",
                                 "props": {"data": [1, 5, 3], "kind": "bar"}})
        line = compile_component({"type": "chart", "id": "c2",
                                  "props": {"data": [1, 5, 3], "kind": "line"}})
        assert "<svg" in bar and "rect" in bar
        assert "polyline" in line

    def test_static_preview(self):
        c = HEPCompiler()
        c.feed(SPEC)
        c.flush()
        html = c.render_all()
        assert "周日烤羊腿" in html and "人数" in html and "羊腿重量" in html
