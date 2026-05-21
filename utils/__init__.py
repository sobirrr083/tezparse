"""
converters/__init__.py
-----------------------
Converterlarni avtomatik topish (auto-discovery).

YANGI CONVERTER QO'SHISH UCHUN:
  Faqat XXXXX_myformat.py fayl yarating — bu faylni O'ZGARTIRMANG.
  Tizim 5 xonali ID prefiksli barcha fayllarni o'zi topadi va yuklaydi.

  Fayl nomi formati:  XXXXX_istalgan_nom.py
  Misol:              10002_antest_converter.py

ID diapazonlari (tavsiya):
  10001–19999  →  test/quiz formatlari
  20001–29999  →  hujjat/matn formatlari
  30001–39999  →  jadval/Excel formatlari
  40001–49999  →  maxsus/aralash formatlar
"""

import importlib
import re
from pathlib import Path

from .base import BaseConverter, ConversionResult

# 5 xonali ID bilan boshlanuvchi fayl nomi: 10001_something.py
_ID_PATTERN = re.compile(r"^(\d{5})_.+$")

REGISTRY: list[type[BaseConverter]] = []

# ── Avtomatik yuklash ─────────────────────────────────────────────────────────
_converters_dir = Path(__file__).parent

for _py_file in sorted(_converters_dir.glob("*.py")):
    _match = _ID_PATTERN.match(_py_file.stem)
    if not _match:
        continue                       # __init__.py, base.py va boshqalar o'tkazib yuboriladi

    _module_name = f"converters.{_py_file.stem}"
    try:
        _module = importlib.import_module(_module_name)
    except Exception as e:
        print(f"[converters] ⚠️  {_py_file.name} yuklanmadi: {e}")
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

# Ustuvorlik bo'yicha saralash (katta PRIORITY = birinchi)
REGISTRY.sort(key=lambda cls: cls.PRIORITY, reverse=True)

# ── Yuklanganlarni log qilish ─────────────────────────────────────────────────
def list_converters() -> str:
    """Admin uchun: yuklanган converterlar ro'yxati."""
    if not REGISTRY:
        return "Hech qanday converter topilmadi."
    lines = ["Yuklanган converterlar:\n"]
    for cls in REGISTRY:
        exts = ", ".join(sorted(cls.SUPPORTED_EXTENSIONS)) or "barcha"
        lines.append(
            f"  [{cls.CONVERTER_ID}]  {cls.NAME:<25}  "
            f"priority={cls.PRIORITY:<3}  ext={exts}\n"
            f"           {cls.DESCRIPTION}"
        )
    return "\n".join(lines)


__all__ = ["REGISTRY", "BaseConverter", "ConversionResult", "list_converters"]
from .file_reader import extract_text, SUPPORTED_EXTENSIONS

__all__ = ["extract_text", "SUPPORTED_EXTENSIONS"]
