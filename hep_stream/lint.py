"""审美 lint —— 编译期的设计纪律（DEV_CHARTER / HEP 规则内建）。

原则：审美是编译器的一部分，不是事后评审。spec 进来先过规则，
错误级违规在 strict 模式下阻断 emit，警告级随 op 附带（渲染端可标注）。

规则集：
  L1 icon 必须是 Lucide 名（禁 emoji 图标）          [error]
  L2 字符串 props 禁 emoji 字符                       [warn]
  L3 action/文本禁 alert(                             [error]
  L4 裸十六进制色值 → 提示用 token                    [warn]
  L5 交互件（button/input/slider）必须有 label        [error]
  L6 禁 font-weight:700（Hana 规范 400/500/600）      [warn]
"""
from __future__ import annotations

import re

__all__ = ["LintIssue", "lint_spec"]

_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_FAT = re.compile(r"font-weight\s*:\s*7\d\d")

_INTERACTIVE = {"button", "input", "slider"}


class LintIssue(dict):
    pass


def lint_spec(spec: dict) -> list[dict]:
    issues: list[dict] = []
    ctype = spec.get("type", "")
    props = spec.get("props", {}) or {}

    def add(level: str, rule: str, msg: str) -> None:
        issues.append(LintIssue(level=level, rule=rule, message=msg,
                                spec_id=spec.get("id", "")))

    icon = str(props.get("icon", ""))
    if icon and not re.fullmatch(r"[a-z0-9-]+", icon):
        add("error", "L1", f"icon 必须是 Lucide 名（kebab-case），得到 {icon!r}")

    for key, val in props.items():
        if isinstance(val, str):
            if _EMOJI.search(val):
                add("warn", "L2", f"props.{key} 含 emoji 字符（HEP 规则：图标用 Lucide）")
            if "alert(" in val:
                add("error", "L3", f"props.{key} 含 alert( （禁用，用 note/status 组件）")
            if _HEX.search(val):
                add("warn", "L4", f"props.{key} 含裸色值，建议用设计 token")
            if _FAT.search(val):
                add("warn", "L6", f"props.{key} 含 font-weight:700（规范仅 400/500/600）")

    if ctype in _INTERACTIVE and not str(props.get("label", "")).strip():
        add("error", "L5", f"交互件 {ctype} 必须提供 label（可访问性）")

    return issues
