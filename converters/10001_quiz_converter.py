"""
converters/10001_quiz_converter.py
-----------------------------------
?/=/+ formatidagi testlarni standart A/B/C/D + ANSWER: X formatiga otkazadi.

Kirish:
  ?.Savol matni
  =Nototri javob
  +Togri javob
  =Nototri javob

Chiqish:
  1. Savol matni
      A. Nototri javob
      B. Togri javob
      C. Nototri javob
      ANSWER: B
"""

import re
from .base import BaseConverter, ConversionResult

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

PAT_Q = re.compile(
    r"^\s*(?:\d+\s*[.)]\s*)?\?\.?\s*(.+)",
    re.DOTALL,
)
PAT_Q_ALONE = re.compile(r"^\s*\?\s*$")
PAT_CORRECT = re.compile(r"^\s*\+\.?\s*(.*)", re.DOTALL)
PAT_WRONG   = re.compile(r"^\s*=\.?\s*(.*)", re.DOTALL)
PAT_LETTER_PREFIX = re.compile(r"^[A-Za-z]\s*[.)]\s*")


def _clean(text: str) -> str:
    text = text.strip()
    text = PAT_LETTER_PREFIX.sub("", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _parse_blocks(text: str) -> list:
    lines = text.splitlines()
    blocks = []
    current = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        mq  = PAT_Q.match(line)
        mqa = PAT_Q_ALONE.match(line)
        mc  = PAT_CORRECT.match(line)
        mw  = PAT_WRONG.match(line)

        if (mq or mqa) and not mc and not mw:
            if current is not None:
                blocks.append(current)
            current = {
                "question": mq.group(1).strip() if mq else "",
                "variants": [],
            }
        elif mc and current is not None:
            current["variants"].append({"text": _clean(mc.group(1)), "correct": True})
        elif mw and current is not None:
            current["variants"].append({"text": _clean(mw.group(1)), "correct": False})
        else:
            if current is None:
                pass
            elif current["variants"]:
                current["variants"][-1]["text"] += " " + line
            else:
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


class QuizConverter(BaseConverter):
    CONVERTER_ID = 10001
    NAME         = "quiz_plus_equal"
    DESCRIPTION  = "?/=/+ format -> A/B/C/D + ANSWER: X"
    SUPPORTED_EXTENSIONS = {".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls"}
    PRIORITY     = 10

    @classmethod
    def can_handle(cls, text: str) -> bool:
        lines = text.splitlines()
        q_count = sum(1 for l in lines if re.match(r"^\s*\?", l))
        v_count = sum(1 for l in lines if re.match(r"^\s*[+=]", l))
        return q_count >= 1 and v_count >= 2

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
                errors.append(f"Blok {i+1} otkazildi [{', '.join(issues)}]: {q_preview}")
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
