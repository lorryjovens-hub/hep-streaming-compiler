"""增量 spec 解析器 —— 流式编译器的第一段。

协议（HEP-Stream Spec v0）：
  模型在回复中流式输出 ```hep 围栏，围栏内每行一个完整的 JSON op：
    {"op":"create","id":"a1","type":"slider","props":{...},"parent":"root"}
    {"op":"patch","id":"a1","props":{"value": 6}}
    {"op":"remove","id":"a1"}
  行完成即解析即编译——真正的边吐字边长界面，无需等整段。

容错纪律：不完整行只缓冲不报错；围栏外的聊天文本忽略；flush() 时
残余行尽力解析（容忍模型截断）。坏行进 bad_lines 留痕，不静默。
"""
from __future__ import annotations

import json
import re
from typing import Iterator

__all__ = ["SpecParser"]

_FENCE_OPEN = re.compile(r"```hep\s*$", re.M)


class SpecParser:
    def __init__(self):
        self._buf = ""            # 未处理的流文本
        self._line_buf = ""       # 围栏内未完成的行
        self._in_fence = False
        self.bad_lines: list[str] = []

    def feed(self, chunk: str) -> list[dict]:
        """喂入一段流文本，返回此刻已完成的 spec ops（顺序保持）。"""
        self._buf += chunk
        ops: list[dict] = []
        while self._buf:
            if not self._in_fence:
                m = _FENCE_OPEN.search(self._buf)
                if m is None:
                    # 只保留尾部潜在的开栏前缀（防 \"```he\" + \"p\\n\" 被切开）
                    keep = min(len(self._buf), 8)
                    self._buf = self._buf[-keep:]
                    break
                self._buf = self._buf[m.end():]
                self._in_fence = True
            else:
                close = self._buf.find("```")
                segment, rest = (self._buf, "") if close == -1 else \
                    (self._buf[:close], self._buf[close + 3:])
                lines = (self._line_buf + segment).split("\n")
                self._line_buf = lines[-1]
                for line in lines[:-1]:
                    op = self._parse_line(line)
                    if op is not None:
                        ops.append(op)
                self._buf = rest
                if close != -1:
                    self._in_fence = False
        return ops

    def flush(self) -> list[dict]:
        """流结束：围栏内残余行尽力解析（容忍截断丢弃）。"""
        ops: list[dict] = []
        if self._in_fence and self._line_buf.strip():
            op = self._parse_line(self._line_buf)
            if op is not None:
                ops.append(op)
        self._line_buf = ""
        self._buf = ""
        self._in_fence = False
        return ops

    def _parse_line(self, line: str) -> dict | None:
        s = line.strip()
        if not s:
            return None
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            self.bad_lines.append(s[:160])
            return None
        if isinstance(obj, dict) and obj.get("op") in ("create", "patch", "remove"):
            return obj
        self.bad_lines.append(s[:160])
        return None
