"""设计馆桥（asset-vault）—— 编译目标从 vault 取材，不手写。

LAAP 设计馆（D:\\LAAP\\asset-vault）是"拿什么设计"的官方资产库：
components/{design-source}/*.html 组件块 · icons/{lucide-static,heroicons,
iconoir,tabler-icons} · index.json 清单。本模块把它接入 HEP 编译器：

  1. 组件块 -> catalog 自定义组件（vault:shadcn-ui/04-block 形式）
  2. 图标解析 -> lucide-static SVG 优先，回退内建精简集
"""
from __future__ import annotations

import json
import re
from pathlib import Path

__all__ = ["VAULT_ROOT", "vault_available", "list_blocks", "load_block",
           "vault_icon", "vault_summary"]

VAULT_ROOT = Path(r"D:\LAAP\asset-vault")


def vault_available() -> bool:
    return VAULT_ROOT.is_dir()


def _icon_dirs() -> list[Path]:
    base = VAULT_ROOT / "icons"
    return [d for d in (base / "lucide-static", base / "iconoir",
                        base / "heroicons", base / "tabler-icons")
            if d.is_dir()]


def vault_icon(name: str, size: int = 16) -> str:
    """从设计馆图标库取 SVG（lucide-static 优先）；取不到返回空串。"""
    for d in _icon_dirs():
        for p in d.rglob(f"{name}.svg"):
            try:
                svg = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            svg = re.sub(r"\s(width|height)=\"[^\"]*\"", "", svg, count=2)
            svg = svg.replace("<svg", f'<svg width="{size}" height="{size}"', 1)
            return re.sub(r"\s+", " ", svg).strip()
    return ""


def list_blocks() -> list[dict]:
    """列出全部设计馆组件块：{ref, source, name, path, bytes}。"""
    out: list[dict] = []
    comp = VAULT_ROOT / "components"
    if not comp.is_dir():
        return out
    for source_dir in sorted(comp.iterdir()):
        if not source_dir.is_dir():
            continue
        for f in sorted(source_dir.glob("*.html")):
            out.append({
                "ref": f"vault:{source_dir.name}/{f.stem}",
                "source": source_dir.name,
                "name": f.stem,
                "path": str(f),
                "bytes": f.stat().st_size,
            })
    return out


def load_block(ref: str) -> str | None:
    """按 ref（vault:source/name）取组件块 HTML。"""
    if not ref.startswith("vault:"):
        return None
    rel = ref[len("vault:"):]
    if "/" not in rel:
        return None
    source, name = rel.split("/", 1)
    f = VAULT_ROOT / "components" / source / f"{name}.html"
    return f.read_text(encoding="utf-8", errors="ignore") if f.is_file() else None


def vault_summary() -> dict:
    """设计馆概览（catalog 页/诊断用）。"""
    blocks = list_blocks()
    by_source: dict[str, int] = {}
    for b in blocks:
        by_source[b["source"]] = by_source.get(b["source"], 0) + 1
    return {
        "available": vault_available(),
        "blocks": len(blocks),
        "sources": by_source,
        "icon_sets": [p.name for p in _icon_dirs()],
    }
