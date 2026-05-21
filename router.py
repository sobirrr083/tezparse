"""
router.py
----------
Fayl matnini tahlil qilib to'g'ri converterni topadi va ishlatadi.

Ishlash tartibi:
  1. Fayldan matn chiqariladi (utils.file_reader)
  2. REGISTRY dagi har bir converter can_handle() tekshiriladi
     (PRIORITY bo'yicha katta → kichik tartibda)
  3. Birinchi mos kelgan converter convert() ni chaqiradi
  4. Agar hech kim mos kelmasa — xato qaytariladi
"""

import logging
from pathlib import Path

from utils.file_reader import extract_text, SUPPORTED_EXTENSIONS
from converters import REGISTRY
from converters.base import ConversionResult

logger = logging.getLogger(__name__)


class UnsupportedFormatError(Exception):
    """Fayl formati qo'llab-quvvatlanmaydi."""


class NoConverterFoundError(Exception):
    """Matn uchun mos converter topilmadi."""


def route(filepath: str) -> ConversionResult:
    """
    Faylni o'qib, mos converterni topib, natijani qaytaradi.

    Parametrlar:
        filepath: lokal fayl yo'li

    Qaytaradi:
        ConversionResult

    Ko'taradi:
        UnsupportedFormatError — fayl kengaytmasi noto'g'ri
        NoConverterFoundError  — matn uchun converter yo'q
        ImportError            — kerakli kutubxona o'rnatilmagan
    """
    ext = Path(filepath).suffix.lower()

    # 1. Kengaytmani tekshirish
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"'{ext}' formatdagi fayllar qabul qilinmaydi.\n"
            f"Qabul qilinadigan formatlar: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # 2. Matn chiqarish
    logger.info(f"Fayl o'qilmoqda: {filepath}")
    text = extract_text(filepath)

    if not text or not text.strip():
        raise NoConverterFoundError("Fayl bo'sh yoki matn o'qib bo'lmadi.")

    # 3. Converter topish
    for converter_cls in REGISTRY:
        # Kengaytma filtr (bo'sh set = hammasi)
        if (
            converter_cls.SUPPORTED_EXTENSIONS
            and ext not in converter_cls.SUPPORTED_EXTENSIONS
        ):
            continue

        if converter_cls.can_handle(text):
            logger.info(f"Converter topildi: {converter_cls.NAME}")
            result = converter_cls.convert(text)
            result.converter_name = converter_cls.NAME
            result.converter_id   = converter_cls.CONVERTER_ID
            return result

    # 4. Hech kim mos kelmadi
    raise NoConverterFoundError(
        f"Fayl mazmuni tanilmadi.\n"
        f"Qo'llab-quvvatlangan formatlar:\n"
        + "\n".join(f"  • {c.NAME}: {c.DESCRIPTION}" for c in REGISTRY)
    )
