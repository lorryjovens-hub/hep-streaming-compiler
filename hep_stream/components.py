"""HEP 原子组件注册表 —— 流式编译器的编译目标。

设计原则（对应 GPT-6 Intelligent UI 三件套之"原子组件库"）：
  1. 组件是【编译目标】不是生成的代码——类型化、预封装、统一设计语言；
  2. 每个组件三件套：schema（props 校验）+ render（静态 HTML）+ ops 语义；
  3. 设计纪律内建：Lucide 图标（禁 emoji）、可访问性（焦点环自动注入）、
     纸感 token（CSS 变量），符合 HEP 生成页面规则与 DEV_CHARTER。

渲染契约：render(props) -> HTML 字符串。浏览器端由 runtime.js 增量挂载。
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ["ComponentError", "Component", "REGISTRY", "compile_component",
           "LUCIDE_MINIMAL"]

# Lucide 精简集（与 LAAP intent_mapper 的 lucide_icon 同族，SVG stroke 风格）
LUCIDE_MINIMAL = {
    "check", "x", "plus", "minus", "arrow-right", "arrow-left", "chevron-down",
    "chevron-right", "search", "settings", "user", "home", "folder", "file",
    "calendar", "clock", "chart-bar", "chart-line", "table", "link", "mail",
    "bell", "star", "heart", "download", "upload", "play", "pause", "refresh",
    "globe", "lock", "unlock", "info", "alert-triangle", "check-circle",
}

_ICON_PATHS = {
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "minus": '<line x1="5" y1="12" x2="19" y2="12"/>',
    "arrow-right": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "chevron-down": '<polyline points="6 9 12 15 18 9"/>',
    "chevron-right": '<polyline points="9 18 15 12 9 6"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
    "chart-bar": '<rect x="4" y="12" width="4" height="8"/><rect x="10" y="8" width="4" height="12"/><rect x="16" y="4" width="4" height="16"/>',
    "chart-line": '<polyline points="3 17 9 11 13 15 21 6"/>',
    "table": '<rect x="3" y="4" width="18" height="16"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="9" y1="10" x2="9" y2="20"/>',
    "info": '<circle cx="12" cy="12" r="9"/><line x1="12" y1="11" x2="12" y2="16"/><line x1="12" y1="8" x2="12" y2="8"/>',
    "alert-triangle": '<path d="M12 3 2 20h20z"/><line x1="12" y1="10" x2="12" y2="14"/><line x1="12" y1="17" x2="12" y2="17"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><polyline points="8 12 11 15 16 9"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14 0 18M12 3c-3 3.5-3 14 0 18"/>',
}


def lucide_icon(name: str, size: int = 16) -> str:
    """Lucide 风格线性 SVG 图标（HEP 规则：禁 emoji，一律 Lucide）。
    设计馆（asset-vault）图标优先，回退内建精简集。"""
    if name in _ICON_PATHS:
        pass
    else:
        try:
            from .vault import vault_icon
            svg = vault_icon(name, size)
            if svg:
                return svg
        except Exception:
            pass
        name = "info" if name in LUCIDE_MINIMAL else ""
        if not name:
            return ""
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{_ICON_PATHS[name]}</svg>')


class ComponentError(ValueError):
    pass


@dataclass
class Component:
    name: str
    required: tuple = ()
    optional: tuple = ()
    render: Callable[[dict, str], str] = field(repr=False, default=None)


def _esc(x: Any) -> str:
    return html.escape(str(x), quote=True)


def _style(**kw) -> str:
    return ";".join(f"{k.replace('_','-')}:{v}" for k, v in kw.items())


# ---------------------------------------------------------------- 基础排印

def _heading(p: dict, cid: str) -> str:
    lvl = int(p.get("level", 2))
    lvl = min(3, max(1, lvl))
    return (f"<h{lvl} id=\"{_esc(cid)}\" style=\"font-family:var(--font-serif);"
            f"font-weight:500;color:var(--text);margin:.6em 0 .3em\">{_esc(p['text'])}</h{lvl}>")


def _text(p: dict, cid: str) -> str:
    tone = {"muted": "var(--text-muted)", "accent": "var(--accent)"}.get(
        p.get("tone", ""), "var(--text)")
    size = {"sm": ".78rem", "lg": "1.05rem"}.get(p.get("size", ""), ".88rem")
    return (f"<p id=\"{_esc(cid)}\" style=\"font-family:var(--font-serif);"
            f"font-size:{size};line-height:1.65;color:{tone};margin:.35em 0\">"
            f"{_esc(p['text'])}</p>")


def _divider(p: dict, cid: str) -> str:
    return (f"<hr id=\"{_esc(cid)}\" style=\"border:none;border-top:.5px solid "
            f"var(--border);margin:.8em 0\">")


def _note(p: dict, cid: str) -> str:
    icon = lucide_icon(p.get("icon", "info"))
    return (f"<div id=\"{_esc(cid)}\" style=\"display:flex;gap:8px;align-items:flex-start;"
            f"background:rgba(83,125,150,.08);border-left:2px solid var(--accent);"
            f"padding:8px 12px;border-radius:0;font-family:var(--font-serif);"
            f"font-size:.84rem;color:var(--text)\">"
            f"<span style=\"color:var(--accent);flex:none;margin-top:2px\">{icon}</span>"
            f"<span>{_esc(p['text'])}</span></div>")


# ---------------------------------------------------------------- 交互件

def _button(p: dict, cid: str) -> str:
    icon = lucide_icon(p.get("icon", "")) if p.get("icon") else ""
    primary = p.get("variant", "primary") == "primary"
    bg = "background:var(--accent);color:#FFFDF7" if primary else \
        "background:transparent;color:var(--accent);border:.5px solid var(--border)"
    return (f"<button id=\"{_esc(cid)}\" data-hep-action=\"{_esc(p.get('action',''))}\" "
            f"style=\"{bg};border-radius:var(--radius-chat-card);padding:6px 14px;"
            f"font-family:var(--font-ui);font-size:.82rem;font-weight:500;"
            f"cursor:pointer;display:inline-flex;align-items:center;gap:6px\" "
            f"aria-label=\"{_esc(p.get('label',''))}\">{icon}{_esc(p.get('label','Button'))}</button>")


def _input(p: dict, cid: str) -> str:
    label = _esc(p.get("label", "输入"))
    return (f"<label id=\"{_esc(cid)}\" style=\"display:flex;flex-direction:column;"
            f"gap:4px;font-family:var(--font-ui);font-size:.78rem;color:var(--text-muted)\">{label}"
            f"<input data-hep-input=\"{_esc(p.get('bind', cid))}\" "
            f"placeholder=\"{_esc(p.get('placeholder',''))}\" "
            f"style=\"background:var(--bg-card);border:.5px solid var(--border);"
            f"border-radius:var(--radius-chat-card);padding:6px 10px;"
            f"font-family:var(--font-ui);font-size:.85rem;color:var(--text)\"></label>")


def _slider(p: dict, cid: str) -> str:
    label = _esc(p.get("label", ""))
    return (f"<label id=\"{_esc(cid)}\" style=\"display:flex;flex-direction:column;"
            f"gap:4px;font-family:var(--font-ui);font-size:.78rem;color:var(--text-muted)\">{label}"
            f"<input type=\"range\" min=\"{_esc(p.get('min',0))}\" "
            f"max=\"{_esc(p.get('max',100))}\" value=\"{_esc(p.get('value',0))}\" "
            f"data-hep-input=\"{_esc(p.get('bind', cid))}\" style=\"width:170px\">"
            f"<span data-hep-echo=\"{_esc(p.get('bind', cid))}\" "
            f"style=\"color:var(--accent);font-variant-numeric:tabular-nums\">"
            f"{_esc(p.get('value',0))}</span></label>")


def _stat(p: dict, cid: str) -> str:
    return (f"<div id=\"{_esc(cid)}\" style=\"min-width:72px\">"
            f"<div style=\"font-size:.75rem;color:var(--text-muted);"
            f"font-family:var(--font-ui)\">{_esc(p.get('label',''))}</div>"
            f"<div style=\"font-size:1.5rem;font-weight:600;color:var(--accent);"
            f"font-family:var(--font-ui);font-variant-numeric:tabular-nums\">"
            f"{_esc(p.get('value','—'))}</div></div>")


def _progress(p: dict, cid: str) -> str:
    pct = max(0, min(100, int(p.get("value", 0))))
    return (f"<div id=\"{_esc(cid)}\" style=\"display:flex;flex-direction:column;gap:4px\">"
            f"<div style=\"height:6px;background:rgba(83,125,150,.15);border-radius:99px\">"
            f"<div style=\"width:{pct}%;height:100%;background:var(--accent);"
            f"border-radius:99px\"></div></div>"
            f"<span style=\"font-size:.72rem;color:var(--text-muted);"
            f"font-family:var(--font-ui)\">{_esc(p.get('label',''))} {pct}%</span></div>")


def _checklist(p: dict, cid: str) -> str:
    items = p.get("items", [])
    rows = "".join(
        f"<li style=\"display:flex;gap:8px;align-items:center;padding:3px 0\">"
        f"<span style=\"color:var(--accent)\">{lucide_icon('check', 14)}</span>"
        f"<span style=\"font-family:var(--font-serif);font-size:.84rem;"
        f"color:var(--text)\">{_esc(i)}</span></li>" for i in items)
    return (f"<ul id=\"{_esc(cid)}\" style=\"list-style:none;margin:.4em 0\">{rows}</ul>")


def _card(p: dict, cid: str) -> str:
    icon = lucide_icon(p.get("icon", "file"), 18)
    return (f"<div id=\"{_esc(cid)}\" style=\"background:var(--bg-card);"
            f"border:.5px solid var(--border);border-radius:var(--radius-chat-card);"
            f"padding:14px 16px\">"
            f"<div style=\"display:flex;align-items:center;gap:8px;margin-bottom:8px\">"
            f"<span style=\"color:var(--accent)\">{icon}</span>"
            f"<span style=\"font-family:var(--font-ui);font-weight:500;"
            f"font-size:.95rem;color:var(--text)\">{_esc(p.get('title',''))}</span></div>"
            f"<div style=\"font-family:var(--font-serif);font-size:.86rem;"
            f"color:var(--text-light)\">{_esc(p.get('body',''))}</div></div>")


def _chart(p: dict, cid: str) -> str:
    data = [float(x) for x in p.get("data", [])][:24]
    if not data:
        data = [0]
    lo, hi = min(data), max(data)
    span = (hi - lo) or 1.0
    n = len(data)
    kind = p.get("kind", "bar")
    if kind == "line":
        pts = " ".join(
            f"{20 + i * (320 / max(1, n - 1)):.1f},{110 - (v - lo) / span * 90:.1f}"
            for i, v in enumerate(data))
        marks = (f"<polyline points=\"{pts}\" fill=\"none\" stroke=\"var(--accent)\" "
                 f"stroke-width=\"2\"/>")
    else:
        w = 320 / n
        marks = "".join(
            f"<rect x=\"{20 + i * w + w*0.18:.1f}\" y=\"{110 - (v - lo) / span * 90:.1f}\" "
            f"width=\"{w*0.64:.1f}\" height=\"{(v - lo) / span * 90:.1f}\" "
            f"fill=\"var(--accent)\" opacity=\".8\"/>" for i, v in enumerate(data))
    return (f"<figure id=\"{_esc(cid)}\" style=\"margin:.4em 0\">"
            f"<svg viewBox=\"0 0 360 130\" style=\"width:100%;max-width:360px\">"
            f"<line x1=\"20\" y1=\"110\" x2=\"345\" y2=\"110\" stroke=\"var(--border)\"/>"
            f"{marks}</svg>"
            f"<figcaption style=\"font-size:.72rem;color:var(--text-muted);"
            f"font-family:var(--font-ui)\">{_esc(p.get('label',''))}</figcaption></figure>")


REGISTRY: dict[str, Component] = {
    "heading": Component("heading", ("text",), ("level",), _heading),
    "text": Component("text", ("text",), ("tone", "size"), _text),
    "divider": Component("divider", (), (), _divider),
    "note": Component("note", ("text",), ("icon",), _note),
    "button": Component("button", ("label",), ("action", "variant", "icon"), _button),
    "input": Component("input", (), ("label", "placeholder", "bind"), _input),
    "slider": Component("slider", (), ("label", "min", "max", "value", "bind"), _slider),
    "stat": Component("stat", ("label", "value"), (), _stat),
    "progress": Component("progress", (), ("label", "value"), _progress),
    "checklist": Component("checklist", ("items",), (), _checklist),
    "card": Component("card", ("title",), ("body", "icon"), _card),
    "chart": Component("chart", ("data",), ("kind", "label"), _chart),
}


def compile_component(spec: dict) -> str:
    """组件 spec -> 静态 HTML。校验 required props 后渲染。
    ``vault:source/name`` ref 直接取设计馆组件块（不手写设计）。"""
    ctype = spec.get("type", "")
    if ctype.startswith("vault:"):
        from .vault import load_block
        html_block = load_block(ctype)
        if html_block is None:
            raise ComponentError(f"设计馆无此组件块: {ctype!r}")
        cid = spec.get("id") or "hep-vault"
        return f'<div id="{_esc(cid)}" data-hep-vault="{_esc(ctype)}">{html_block}</div>'
    comp = REGISTRY.get(ctype)
    if comp is None:
        raise ComponentError(f"未知组件类型: {ctype!r}（可用: {', '.join(sorted(REGISTRY))}）")
    props = spec.get("props", {}) or {}
    missing = [k for k in comp.required if k not in props]
    if missing:
        raise ComponentError(f"组件 {ctype} 缺少必需 props: {missing}")
    cid = spec.get("id") or f"hep-{ctype}"
    return comp.render(props, cid)
