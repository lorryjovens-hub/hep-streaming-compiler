"""HEP 流式编译器 —— token 流 → RenderOp 流。

GPT-6 Intelligent UI 的核心是"即时流式编译器"：模型吐 token 的同时
界面逐帧生长。本模块是 LAAP 版实现：

    token 流 ──SpecParser──▶ spec ops ──lint──▶ 组件编译 ──▶ RenderOps
        （增量）          （审美纪律）   （编译目标）    （增量 emit）

RenderOp 契约（给宿主/浏览器 runtime 消费）：
    {"op":"append","target":"root"|"#id","id":"a1","html":"..."}
    {"op":"patch","id":"a1","props":{"value":6}}     # 运行时联动更新
    {"op":"remove","id":"a1"}
    {"op":"lint","id":"a1","issues":[...]}           # 审美诊断（可选下发）

宿主无关：Hana 卡片（card:request/response）、Showcard、普通浏览器
（runtime.js）都可以消费同一 op 流——这就是"编译式组件"的意义。
"""
from __future__ import annotations

from typing import Any

from .components import ComponentError, compile_component
from .lint import lint_spec
from .parser import SpecParser

__all__ = ["HEPCompiler", "RenderOp"]

RenderOp = dict


class HEPCompiler:
    def __init__(self, strict: bool = False, emit_lint: bool = True):
        self.strict = strict            # True: error 级 lint 违规阻断 emit
        self.emit_lint = emit_lint
        self._parser = SpecParser()
        self.emitted: list[RenderOp] = []
        self.rejected: list[dict] = []

    # ---------------------------------------------------------------- 流入口

    def feed(self, chunk: str) -> list[RenderOp]:
        """喂入一段 token 流，返回此刻新增的 RenderOps（逐帧生长）。"""
        return self._compile(self._parser.feed(chunk))

    def flush(self) -> list[RenderOp]:
        """流结束收尾：残余 spec 尽力编译。"""
        return self._compile(self._parser.flush())

    # ---------------------------------------------------------------- 编译

    def _compile(self, ops: list[dict]) -> list[RenderOp]:
        out: list[RenderOp] = []
        for spec in ops:
            issues = lint_spec(spec) if spec.get("op") == "create" else []
            errors = [i for i in issues if i["level"] == "error"]
            if self.emit_lint and issues:
                out.append({"op": "lint", "id": spec.get("id", ""),
                            "issues": issues})
            if errors and self.strict:
                self.rejected.append({"spec": spec, "issues": errors})
                continue
            try:
                op = self._emit(spec)
            except ComponentError as exc:
                self.rejected.append({"spec": spec, "error": str(exc)})
                continue
            if op is not None:
                out.append(op)
                self.emitted.append(op)
        return out

    def _emit(self, spec: dict) -> RenderOp | None:
        kind = spec["op"]
        if kind == "create":
            html = compile_component(spec)
            return {"op": "append", "target": spec.get("parent", "root"),
                    "id": spec["id"], "html": html}
        if kind == "patch":
            return {"op": "patch", "id": spec["id"],
                    "props": spec.get("props", {})}
        if kind == "remove":
            return {"op": "remove", "id": spec["id"]}
        return None

    # ---------------------------------------------------------------- 便捷

    def render_all(self) -> str:
        """把全部 append op 的 HTML 串成静态预览（测试/降级用）。"""
        return "\n".join(op["html"] for op in self.emitted
                         if op["op"] == "append")

    def stats(self) -> dict[str, Any]:
        return {
            "emitted": len(self.emitted),
            "appends": sum(1 for o in self.emitted if o["op"] == "append"),
            "patches": sum(1 for o in self.emitted if o["op"] == "patch"),
            "rejected": len(self.rejected),
            "bad_lines": len(self._parser.bad_lines),
        }
