"""
converters/10005_hash_plus_minus_converter.py
----------------------------------------------
# / + / - formatidagi testlarni standart A/B/C/D + ANSWER: X ga o'tkazadi.

FORMAT QOIDALARI:
  #  — savol boshlanishi (# dan keyin savol matni)
  +  — to'g'ri javob (faqat bitta bo'lishi kerak)
  -  — noto'g'ri javob (bir yoki bir nechta)

MISOLLAR:
  # Savol matni
  +To'g'ri javob
  -Noto'g'ri 1
  -Noto'g'ri 2
  -Noto'g'ri 3

  # Ko'p qatorli savol
  # davomi (# bilan boshlanuvchi davom qatorlar)
  +Javob
  -Javob 2

  # 1. Raqamli savol ham ishlaydi
  +Togri
  -Notogri
"""

import re
from .base import BaseConverter, ConversionResult

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Qator tipi aniqlash
PAT_QUESTION = re.compile(r"^#\s*(.*)")          # # Savol matni
PAT_CORRECT  = re.compile(r"^\+\s*(.*)")          # +To'g'ri javob
PAT_WRONG    = re.compile(r"^-\s*(.*)")           # -Noto'g'ri javob


def _clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _parse_blocks(text: str) -> list:
    """
    Matnni savol bloklariga ajratish.

    Ko'p qatorli savol qo'llab-quvvatlanadi:
      # Birinchi qator
      # ikkinchi qator  ← shu blokka ulanadi
      +Javob
    """
    lines = text.splitlines()
    blocks = []
    current = None

    for raw in lines:
        line = raw.strip()

        if not line:
            continue

        mq = PAT_QUESTION.match(line)
        mc = PAT_CORRECT.match(line)
        mw = PAT_WRONG.match(line)

        # ── Savol qatori (#) ─────────────────────────────────────────────────
        if mq:
            q_text = _clean(mq.group(1))

            # Agar oldingi blok ham # bilan tugagan va hali variant yo'q bo'lsa
            # — bu ko'p qatorli savolning davomi
            if current is not None and not current["variants"]:
                # Ko'p qatorli savol: # qatorlari birlashtiriladi
                if current["question"]:
                    current["question"] += " " + q_text
                else:
                    current["question"] = q_text
            else:
                # Yangi savol bloki
                if current is not None:
                    blocks.append(current)
                current = {"question": q_text, "variants": []}

            continue

        # ── To'g'ri javob (+) ────────────────────────────────────────────────
        if mc and current is not None:
            v_text = _clean(mc.group(1))
            # Davom qatorlari (keyingi qator # ham, + ham, - ham emas)
            current["variants"].append({"text": v_text, "correct": True})
            continue

        # ── Noto'g'ri javob (-) ──────────────────────────────────────────────
        if mw and current is not None:
            v_text = _clean(mw.group(1))
            current["variants"].append({"text": v_text, "correct": False})
            continue

        # ── Boshqa qator ─────────────────────────────────────────────────────
        if current is not None:
            if current["variants"]:
                # Oxirgi variant davomi
                current["variants"][-1]["text"] += " " + line
            elif current["question"]:
                # Savol davomi
                current["question"] += " " + line

    if current is not None:
        blocks.append(current)

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


class HashPlusMinusConverter(BaseConverter):
    """
    # / + / - formatidagi testlar uchun converter.
    # = savol,  + = to'g'ri javob,  - = noto'g'ri javob
    """

    CONVERTER_ID = 10005
    NAME         = "hash_plus_minus"
    DESCRIPTION  = "# savol / + togri / - notogri formati -> A/B/C/D + ANSWER"
    SUPPORTED_EXTENSIONS = {".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls"}
    PRIORITY     = 15

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        Matndа # bilan boshlanuvchi savol va + / - variantlar bo'lsa — mos.
        """
        lines = text.splitlines()
        q_count = sum(1 for l in lines if re.match(r"^#\s*\S", l.strip()))
        c_count = sum(1 for l in lines if re.match(r"^\+\s*\S", l.strip()))
        m_count = sum(1 for l in lines if re.match(r"^-\s*\S",  l.strip()))
        return q_count >= 1 and c_count >= 1 and m_count >= 1

    @classmethod
    def convert(cls, text: str) -> ConversionResult:
        blocks = _parse_blocks(text)
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
