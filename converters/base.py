"""
converters/base.py
------------------
Barcha converterlar uchun abstract base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ConversionResult:
    success: bool
    output_text: str = ""
    converted_count: int = 0
    skipped_count: int = 0
    errors: list = field(default_factory=list)
    converter_name: str = ""
    converter_id: int = 0


class BaseConverter(ABC):
    CONVERTER_ID: int = 0
    NAME: str = "base"
    DESCRIPTION: str = "Base converter"
    SUPPORTED_EXTENSIONS: set = set()
    PRIORITY: int = 0

    @classmethod
    @abstractmethod
    def can_handle(cls, text: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def convert(cls, text: str) -> ConversionResult:
        pass
