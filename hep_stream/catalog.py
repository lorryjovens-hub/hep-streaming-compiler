"""Catalog 契约层 —— A2UI 能力协商 + 消息映射（做超集，不做仿品）。

对齐 A2UI（a2ui-project/a2ui v0.9.1）的三件：
  1. Catalog = 组件目录契约（JSON Schema 级声明：props/必填/组合约束）
  2. 能力协商：客户端报 supportedCatalogIds，编译端择一产出
  3. 消息映射：RenderOps 可转译为 A2UI 消息（createSurface/
     updateComponents upsert / updateDataModel），换取官方渲染器

自主保留：审美 lint、设计馆资产、Hana 卡片宿主。
"""
from __future__ import annotations

import json
import time
from typing import Any

from .components import REGISTRY, compile_component
from .vault import list_blocks

__all__ = ["CATALOG_FULL", "CATALOG_BASIC", "build_catalog", "negotiate",
           "validate_spec", "to_a2ui_messages"]

CATALOG_FULL = "hep-catalog/1.0"
CATALOG_BASIC = "hep-catalog-basic/1.0"   # 降级公共子集（A2UI Basic Catalog 思路）
_BASIC_TYPES = {"heading", "text", "button", "input", "divider", "stat"}


def build_catalog(include_vault: bool = True) -> dict[str, Any]:
    """REGISTRY + 设计馆组件块 -> catalog 契约（JSON 可序列化）。"""
    comps: dict[str, Any] = {}
    for name, comp in REGISTRY.items():
        comps[name] = {
            "type": name,
            "required": list(comp.required),
            "optional": list(comp.optional),
            "props": {k: {"type": "string"} for k in (*comp.required, *comp.optional)},
        }
    if include_vault:
        for b in list_blocks():
            comps[b["ref"]] = {
                "type": "vault-block",
                "ref": b["ref"],
                "source": b["source"],
                "bytes": b["bytes"],
                "required": [],
                "optional": [],
                "props": {},
            }
    return {
        "id": CATALOG_FULL,
        "version": "1.0",
        "generated_at": time.time(),
        "components": comps,
        "instructions": "icon 必须 Lucide 名；交互件必填 label；色值用 token。",
    }


def negotiate(supported_catalog_ids: list[str],
              prefer: str = CATALOG_FULL) -> dict[str, Any]:
    """能力协商：客户端声明支持的 catalog，返回选定 catalog 或报错。"""
    if not supported_catalog_ids:
        # 未声明 = 只发公共子集（保守降级，A2UI 同思路）
        comps = {k: v for k, v in build_catalog()["components"].items()
                 if k in _BASIC_TYPES}
        return {"id": CATALOG_BASIC, "version": "1.0", "components": comps,
                "degraded": True}
    if prefer in supported_catalog_ids:
        return {"id": prefer, "degraded": False, **build_catalog()}
    if CATALOG_BASIC in supported_catalog_ids:
        comps = {k: v for k, v in build_catalog()["components"].items()
                 if k in _BASIC_TYPES}
        return {"id": CATALOG_BASIC, "version": "1.0", "components": comps,
                "degraded": True}
    raise ValueError(f"无可协商的 catalog：客户端只支持 {supported_catalog_ids}")


def validate_spec(spec: dict, catalog: dict) -> list[str]:
    """按 catalog 契约校验 spec（A2UI：不在 catalog 内判非法，不回退）。"""
    errors: list[str] = []
    ctype = spec.get("type", "")
    comps = catalog.get("components", {})
    if ctype not in comps and not ctype.startswith("vault:"):
        errors.append(f"Invalid component type: {ctype!r} 不在协商的 catalog 中")
        return errors
    if ctype in comps:
        props = spec.get("props", {}) or {}
        missing = [k for k in comps[ctype].get("required", []) if k not in props]
        if missing:
            errors.append(f"{ctype} 缺少必需 props: {missing}")
    return errors


def to_a2ui_messages(ops: list[dict], surface_id: str = "hep-surface",
                     version: int = 1) -> list[dict]:
    """RenderOps -> A2UI 风格消息（JSONL 可序列化），供官方渲染器消费。

    映射：
      append -> updateComponents（按 ID upsert，children 父引用）
      patch  -> updateDataModel（JSON Pointer 路径级 set）
      remove -> updateComponents（父 children 移除）
    """
    msgs: list[dict] = [{"version": version, "surfaceId": surface_id,
                         "type": "createSurface", "surfaceId_": surface_id,
                         "catalogId": CATALOG_FULL}]
    for op in ops:
        if op.get("op") == "append":
            msgs.append({
                "version": version, "surfaceId": surface_id,
                "type": "updateComponents",
                "components": [{
                    "id": op["id"], "component": "RawHtml",
                    "html": op.get("html", ""),
                    "parent": op.get("target", "root"),
                }],
            })
        elif op.get("op") == "patch":
            msgs.append({
                "version": version, "surfaceId": surface_id,
                "type": "updateDataModel",
                "updates": [{"path": f"/{op['id']}", "value": op.get("props", {})}],
            })
        elif op.get("op") == "remove":
            msgs.append({
                "version": version, "surfaceId": surface_id,
                "type": "updateComponents",
                "removeIds": [op["id"]],
            })
    return msgs
