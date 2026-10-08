"""HEP Streaming Compiler —— LAAP 的原生流式 GUI 编译器。

对话用来造，界面用来用。
"""
from .components import REGISTRY, ComponentError, compile_component, lucide_icon
from .compiler import HEPCompiler
from .catalog import build_catalog, negotiate, to_a2ui_messages, validate_spec
from .lint import lint_spec
from .parser import SpecParser
from .vault import list_blocks, load_block, vault_summary

__version__ = "0.2.0"

__all__ = [
    "HEPCompiler", "SpecParser", "lint_spec", "compile_component",
    "lucide_icon", "REGISTRY", "ComponentError",
    "build_catalog", "negotiate", "validate_spec", "to_a2ui_messages",
    "list_blocks", "load_block", "vault_summary", "__version__",
]
