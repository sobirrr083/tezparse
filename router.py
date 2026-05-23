"""
router.py
----------
Faylni oqib, mos converterni topib, natijani qaytaradi.
"""

import logging
from pathlib import Path

from utils.file_reader import extract_text, SUPPORTED_EXTENSIONS
from converters import REGISTRY
from converters.base import ConversionResult

logger = logging.getLogger(__name__)


class UnsupportedFormatError(Exception):
    pass


class NoConverterFoundError(Exception):
    pass


def route(filepath: str) -> ConversionResult:
    ext = Path(filepath).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"'{ext}' formati qabul qilinmaydi.\n"
            f"Qabul qilinadigan formatlar: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    logger.info(f"Fayl oqilmoqda: {filepath}")
    text = extract_text(filepath)

    if not text or not text.strip():
        raise NoConverterFoundError("Fayl bosh yoki matn oqub bolmadi.")

    for converter_cls in REGISTRY:
        if (
            converter_cls.SUPPORTED_EXTENSIONS
            and ext not in converter_cls.SUPPORTED_EXTENSIONS
        ):
            continue
        if converter_cls.can_handle(text):
            logger.info(f"Converter topildi: {converter_cls.NAME} [ID:{converter_cls.CONVERTER_ID}]")
            result = converter_cls.convert(text)
            result.converter_name = converter_cls.NAME
            result.converter_id   = converter_cls.CONVERTER_ID
            return result

    raise NoConverterFoundError(
        "Fayl mazmuni tanilmadi.\n"
        + "\n".join(f"  - {c.NAME}: {c.DESCRIPTION}" for c in REGISTRY)
    )
