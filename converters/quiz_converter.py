"""
converters/quiz_converter.py
-----------------------------
?/=/+ formatidagi testlarni standart A/B/C/D + ANSWER: X formatiga o'tkazadi.

Format qoidalari:
  ?  yoki ?. — savol boshlanishi
  +  yoki +. — to'g'ri variant
  =  yoki =. — noto'g'ri variant

Misol kirish:
  ?.Biofizika nima o'rganadi?
  =Kimyoviy jarayonlarni
  +Biologik ob'ektlarning fizik xossalarini
  =Fiziologik jarayonlarni

Misol chiqish:
  1. Biofizika nima o'rganadi?

      A. Kimyoviy jarayonlarni
      B. Biologik ob'ektlarning fizik xossalarini
      C. Fiziologik jarayonlarni

      ANSWER: B
"""

import re
from .base import BaseConverter, ConversionResult

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ── Regex patternlar ──────────────────────────────────────────────────────────

# Savol: "? Savol matni" yoki "?. Savol" yoki "1. ? Savol"
PAT_Q = re.compile(
    r"^\s*"
    r"(?:\d+\s*[.)]\s*)?"   # ixtiyoriy raqam: "1. " yoki "1) "
    r"\?\.?\s*"              # ? belgisi, ixtiyoriy nuqta, ixtiyoriy bo'shliq
    r"(.+)",                 # kamida 1 belgi savol matni (bo'sh satr emas)
    re.DOTALL,
)
PAT_Q_ALONE = re.compile(r"^\s*\?\s*$")   # faqat "?" — savol keyingi qatorda

# Variantlar
PAT_CORRECT = re.compile(r"^\s*\+\.?\s*(.*)", re.DOTALL)  # to'g'ri variant (+)
PAT_WRONG   = re.compile(r"^\s*=\.?\s*(.*)", re.DOTALL)   # noto'g'ri variant (=)

# Variant boshidagi "A. " "B) " kabi prefikslarni tozalash
PAT_LETTER_PREFIX = re.compile(r"^[A-Za-z]\s*[.)]\s*")


def _clean(text: str) -> str:
    """Matnni tozalash: ortiqcha bo'shliq, harf prefikslari."""
    text = text.strip()
    text = PAT_LETTER_PREFIX.sub("", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _parse_blocks(text: str) -> list:
    """
    Matnni savol bloklariga ajratish.
    Qaytaradi: [{'question': str, 'variants': [{'text': str, 'correct': bool}]}]
    """
    lines = text.splitlines()
    blocks = []
    current = None
    prefix_buf = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        mq  = PAT_Q.match(line)
        mqa = PAT_Q_ALONE.match(line)
        mc  = PAT_CORRECT.match(line)
        mw  = PAT_WRONG.match(line)

        if (mq or mqa) and not mc and not mw:
            # Yangi savol bloki boshlandi
            if current is not None:
                blocks.append(current)
            current = {
                "question": mq.group(1).strip() if mq else "",
                "variants": [],
            }
            prefix_buf = []

        elif mc and current is not None:
            current["variants"].append({"text": _clean(mc.group(1)), "correct": True})

        elif mw and current is not None:
            current["variants"].append({"text": _clean(mw.group(1)), "correct": False})

        else:
            if current is None:
                prefix_buf.append(line)
            elif current["variants"]:
                # Oxirgi variantning davomi (qator ko'chirish bilan yozilgan)
                current["variants"][-1]["text"] += " " + line
            else:
                # Savolning davomi
                current["question"] += " " + line

    if current is not None:
        blocks.append(current)

    return blocks


def _validate(block: dict) -> list:
    """Blok muammolarini topib ro'yxat qaytaradi."""
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
    """Blokni chiqish formatiga o'tkazish."""
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


# ── Converter class ───────────────────────────────────────────────────────────

class QuizConverter(BaseConverter):
    """?/=/+ formatidagi testlar uchun converter."""

    NAME        = "quiz_plus_equal"
    DESCRIPTION = "?/=/+ format → A/B/C/D + ANSWER: X"
    SUPPORTED_EXTENSIONS = {".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls"}
    PRIORITY    = 10

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Matndagi ?/+/= markerlar soniga qarab aniqlash.
        Kamida 1 ta savol va 2 ta variant belgisi bo'lishi kerak.
        """
        lines = text.splitlines()
        q_count = sum(1 for l in lines if re.match(r"^\s*\?", l))
        v_count = sum(1 for l in lines if re.match(r"^\s*[+=]", l))
        return q_count >= 1 and v_count >= 2

    @classmethod
    def convert(cls, text: str) -> ConversionResult:
        blocks  = _parse_blocks(text)
        parts   = []
        errors  = []
        q_num   = 1

        for i, block in enumerate(blocks):
            issues = _validate(block)
            if issues:
                q_preview = block["question"][:60] or "(savol bo'sh)"
                errors.append(
                    f"Blok {i+1} o'tkazildi [{', '.join(issues)}]: {q_preview}..."
                )
                continue

            parts.append(_format_block(block, q_num))
            q_num += 1

        return ConversionResult(
            success        = bool(parts),
            output_text    = "\n".join(parts),
            converted_count= q_num - 1,
            skipped_count  = len(errors),
            errors         = errors,
            converter_name = cls.NAME,
        )
