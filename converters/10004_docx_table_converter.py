"""
converters/10004_docx_table_converter.py
------------------------------------------
Word (.docx) jadval formatidagi testlarni standart A/B/C/D + ANSWER formatiga otkazadi.

JADVAL TUZILISHI:
  | №  | Savol | To'g'ri javob | Qo'shimcha javob | Qo'shimcha javob | Qo'shimcha javob |
  |----|-------|---------------|------------------|------------------|------------------|
  | 1  | ...   | ...           | ...              | ...              | ...              |

Qoidalar:
  - 1-ustun: tartib raqami (ixtiyoriy, shart emas)
  - 2-ustun: savol matni
  - 3-ustun: TO'G'RI javob (DOIM uchinchi ustun)
  - 4-6-ustun: noto'g'ri javoblar (1 tadan 3 tagacha)

  Minimal ustunlar: 4 (№ + Savol + Togri + 1 notogri)
  Maksimal ustunlar: 6 (№ + Savol + Togri + 3 notogri)

MUHIM:
  - To'g'ri javob DOIM 3-ustunda — pozitsiya saqlanadi
  - Variantlar A/B/C/D tartibida aralashtirib beriladi (togri javob tasodifiy joyga)
  - Sarlavha qatori avtomatik aniqlanib o'tkazib yuboriladi
"""

import random
from pathlib import Path
from .base import BaseConverter, ConversionResult

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Sarlavha qatoridagi kalit sozlar (case-insensitive)
HEADER_KEYWORDS = {
    "savol", "question", "togri", "to'g'ri", "javob", "answer",
    "qoshimcha", "qo'shimcha", "additional", "no", "№", "#"
}


def _is_header_row(cells: list) -> bool:
    """Sarlavha qatorini aniqlash."""
    text = " ".join(cells).lower()
    matches = sum(1 for kw in HEADER_KEYWORDS if kw in text)
    return matches >= 2


def _clean(text: str) -> str:
    """Matnni tozalash."""
    import re
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    # tab, newline larni bo'shliqqa
    text = text.replace("\t", " ").replace("\n", " ")
    return text.strip()


def _parse_docx_table(filepath: str) -> list:
    """
    .docx fayldagi jadvallardan savol bloklarini chiqarish.
    Qaytaradi: [{'question': str, 'variants': [{'text': str, 'correct': bool}]}]
    """
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx kerak: pip install python-docx")

    doc = Document(filepath)
    blocks = []

    for table in doc.tables:
        col_count = len(table.columns)

        # Minimal 4 ustun kerak: № + Savol + Togri + kamida 1 notogri
        if col_count < 4:
            continue

        for row_idx, row in enumerate(table.rows):
            cells = [_clean(cell.text) for cell in row.cells]

            # Bo'sh qatorni o'tkazish
            if not any(cells):
                continue

            # Sarlavha qatorini o'tkazish
            if _is_header_row(cells):
                continue

            # Savol: 2-ustun (index 1)
            # Agar 1-ustun raqam bo'lsa (№) — 2-ustun savol
            # Agar 1-ustun raqam bo'lmasa — 1-ustun savol bo'lishi ham mumkin
            question_idx = 1   # odatda: №(0) | Savol(1) | Togri(2) | ...
            correct_idx  = 2
            wrong_start  = 3

            # Agar birinchi ustun bo'sh yoki raqam emas — savol 1-ustunda
            first = cells[0]
            if first and not first.isdigit() and len(first) > 10:
                # 1-ustunda savol matni bor
                question_idx = 0
                correct_idx  = 1
                wrong_start  = 2

            # Savol va togri javob
            if question_idx >= len(cells) or correct_idx >= len(cells):
                continue

            question = cells[question_idx]
            correct  = cells[correct_idx]

            if not question or not correct:
                continue

            # Noto'g'ri javoblar
            wrong_answers = []
            for i in range(wrong_start, len(cells)):
                if i < len(cells) and cells[i]:
                    wrong_answers.append(cells[i])

            if not wrong_answers:
                continue

            # Variantlarni yig'ish
            variants = [{"text": correct, "correct": True}]
            for w in wrong_answers:
                variants.append({"text": w, "correct": False})

            # Aralashtirib yuborish (togri javob tasodifiy joyda bo'lsin)
            random.shuffle(variants)

            blocks.append({
                "question": question,
                "variants": variants,
            })

    return blocks


def _validate(block: dict) -> list:
    issues = []
    correct = [v for v in block["variants"] if v["correct"]]
    wrong   = [v for v in block["variants"] if not v["correct"]]
    if not block["question"].strip():
        issues.append("empty_question")
    if len(block["variants"]) < 2:
        issues.append("too_few_variants")
    if not correct:
        issues.append("no_correct")
    if len(correct) > 1:
        issues.append("multiple_correct")
    if not wrong:
        issues.append("no_wrong")
    return issues


def _format_block(block: dict, number: int) -> str:
    lines = [f"{number}. {block['question'].strip()}", ""]
    correct_letter = None
    for i, v in enumerate(block["variants"]):
        letter = LETTERS[i] if i < len(LETTERS) else f"?{i}"
        lines.append(f"    {letter}. {v['text']}")
        if v["correct"]:
            correct_letter = letter
    lines.append("")
    lines.append(f"    ANSWER: {correct_letter or '?'}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


class DocxTableConverter(BaseConverter):
    """
    Word (.docx) jadval formatidagi testlar uchun converter.
    Jadval tuzilishi: № | Savol | To'g'ri javob | Qo'shimcha... | ...
    """

    CONVERTER_ID = 10004
    NAME         = "docx_table"
    DESCRIPTION  = "Word jadval (№|Savol|Togri|Notogri...) -> A/B/C/D + ANSWER"
    SUPPORTED_EXTENSIONS = {".docx"}
    PRIORITY     = 30    # ABCD/slash dan ham oldin — docx uchun eng yuqori

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Bu converter matn asosida emas, fayl tipi asosida ishlaydi.
        Matn ichida jadval sarlavhasi kalit sozlari bo'lsa — mos.
        """
        import re
        text_lower = text.lower()
        has_savol  = "savol" in text_lower or "question" in text_lower
        # "To'g'ri javob" — apostroflar har xil kodlashda kelishi mumkin
        # Shuning uchun regex bilan tekshiramiz
        has_javob = bool(re.search(
            r"to.?g.?ri\s+javob|correct\s+answer|togri\s+javob",
            text_lower
        ))
        return has_savol and has_javob

    @classmethod
    def convert(cls, text: str) -> ConversionResult:
        """
        Bu converter 'text' emas, to'g'ridan-to'g'ri faylni o'qiydi.
        _filepath atributi router tomonidan qo'yiladi.
        """
        filepath = getattr(cls, "_filepath", None)
        if not filepath:
            return ConversionResult(
                success=False,
                errors=["DocxTableConverter: filepath berilmadi"],
            )
        return cls._convert_file(filepath)

    @classmethod
    def _convert_file(cls, filepath: str) -> ConversionResult:
        try:
            blocks = _parse_docx_table(filepath)
        except ImportError as e:
            return ConversionResult(success=False, errors=[str(e)])
        except Exception as e:
            return ConversionResult(success=False, errors=[f"Fayl o'qishda xato: {e}"])

        parts  = []
        errors = []
        q_num  = 1

        for i, block in enumerate(blocks):
            issues = _validate(block)
            if issues:
                q_preview = block["question"][:60] or "(savol bosh)"
                errors.append(
                    f"Blok {i+1} otkazildi [{', '.join(issues)}]: {q_preview}"
                )
                continue
            parts.append(_format_block(block, q_num))
            q_num += 1

        return ConversionResult(
            success         = bool(parts),
            output_text     = "\n".join(parts),
            converted_count = q_num - 1,
            skipped_count   = len(errors),
            errors          = errors,
            converter_name  = cls.NAME,
            converter_id    = cls.CONVERTER_ID,
        )
