"""Catalog 契约 + 设计馆桥测试：协商 / 校验 / A2UI 映射 / vault 取材。"""

from __future__ import annotations

import pytest

from hep_stream.catalog import (
    CATALOG_BASIC, CATALOG_FULL, build_catalog, negotiate,
    to_a2ui_messages, validate_spec)
from hep_stream.components import compile_component
from hep_stream.vault import list_blocks, load_block, vault_summary


class TestCatalog:
    def test_build_catalog_has_registry_and_vault(self):
        cat = build_catalog()
        assert "slider" in cat["components"]
        vault_refs = [k for k in cat["components"] if k.startswith("vault:")]
        assert vault_refs, "应收录设计馆组件块"

    def test_negotiate_full_and_fallback(self):
        full = negotiate([CATALOG_FULL])
        assert full["id"] == CATALOG_FULL and not full["degraded"]
        basic = negotiate([])
        assert basic["id"] == CATALOG_BASIC and basic["degraded"]
        assert "slider" not in basic["components"]   # 公共子集不含高级件
        with pytest.raises(ValueError, match="无可协商"):
            negotiate(["unknown-catalog/9"])

    def test_validate_spec_against_catalog(self):
        cat = negotiate([CATALOG_FULL])
        assert validate_spec({"type": "slider", "props": {}}, cat) == []
        errs = validate_spec({"type": "warp-drive", "props": {}}, cat)
        assert errs and "Invalid component type" in errs[0]

    def test_a2ui_message_mapping(self):
        ops = [
            {"op": "append", "target": "root", "id": "a", "html": "<p>x</p>"},
            {"op": "patch", "id": "a", "props": {"value": 6}},
            {"op": "remove", "id": "b"},
        ]
        msgs = to_a2ui_messages(ops, surface_id="s1")
        assert msgs[0]["type"] == "createSurface" and msgs[0]["surfaceId"] == "s1"
        types = [m["type"] for m in msgs[1:]]
        assert types == ["updateComponents", "updateDataModel", "updateComponents"]
        assert msgs[2]["updates"][0]["path"] == "/a"
        assert msgs[3]["removeIds"] == ["b"]


class TestVault:
    def test_list_and_load_block(self):
        blocks = list_blocks()
        assert blocks, "设计馆应有组件块"
        ref = blocks[0]["ref"]
        html = load_block(ref)
        assert html and "<" in html

    def test_vault_ref_compiles(self):
        blocks = list_blocks()
        out = compile_component({"type": blocks[0]["ref"], "id": "v1"})
        assert 'data-hep-vault' in out and blocks[0]["ref"] in out

    def test_unknown_vault_ref_raises(self):
        from hep_stream.components import ComponentError
        with pytest.raises(ComponentError, match="设计馆无此组件块"):
            compile_component({"type": "vault:nope/nothing", "id": "x"})

    def test_vault_summary(self):
        s = vault_summary()
        assert s["available"] and s["blocks"] > 0 and s["icon_sets"]
