"""
converters/__init__.py
-----------------------
5 xonali ID prefiksli barcha converter fayllarini avtomatik topadi.
Yangi converter qoshish uchun faqat XXXXX_nom.py fayl yarating.
"""

import importlib
import re
from pathlib import Path

from .base import BaseConverter, ConversionResult

_ID_PATTERN = re.compile(r"^(\d{5})_.+$")

REGISTRY: list = []

_converters_dir = Path(__file__).parent

for _py_file in sorted(_converters_dir.glob("*.py")):
    if not _ID_PATTERN.match(_py_file.stem):
        continue
    _module_name = f"converters.{_py_file.stem}"
    try:
        _module = importlib.import_module(_module_name)
    except Exception as e:
        print(f"[converters] WARNING: {_py_file.name} yuklanmadi: {e}")
        continue
    for _attr_name in dir(_module):
        _attr = getattr(_module, _attr_name)
        if (
            isinstance(_attr, type)
            and issubclass(_attr, BaseConverter)
            and _attr is not BaseConverter
            and _attr not in REGISTRY
        ):
            REGISTRY.append(_attr)

REGISTRY.sort(key=lambda cls: cls.PRIORITY, reverse=True)


def list_converters() -> str:
    if not REGISTRY:
        return "Hech qanday converter topilmadi."
    lines = ["Yuklangan converterlar:\n"]
    for cls in REGISTRY:
        exts = ", ".join(sorted(cls.SUPPORTED_EXTENSIONS)) or "barcha"
        lines.append(
            f"  [{cls.CONVERTER_ID}]  {cls.NAME:<25}  priority={cls.PRIORITY}  ext={exts}\n"
            f"           {cls.DESCRIPTION}"
        )
    return "\n".join(lines)


__all__ = ["REGISTRY", "BaseConverter", "ConversionResult", "list_converters"]
