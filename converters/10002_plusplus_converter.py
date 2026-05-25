"""
converters/10002_plusplus_converter.py
---------------------------------------
+++/===/# formatidagi testlarni standart A/B/C/D + ANSWER: X formatiga otkazadi.

Format qoidalari:
  +++  (3+ ta '+') — yangi savol boshlanishi
  ===  (3+ ta '=') — variant ajratgichi
  #    — variant boshida kelsa, shu variant TOGRI javob

Kirish misoli:
  +++Savol matni
  ===
  #Togri javob
  ===
  Notogri javob
  ===
  Notogri javob

Chiqish:
  1. Savol matni
      A. Togri javob
      B. Notogri javob
      C. Notogri javob
      ANSWER: A
"""

import re
from .base import BaseConverter, ConversionResult

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

PAT_Q_SEP       = re.compile(r"^\+{3,}")
PAT_V_SEP       = re.compile(r"^={3,}")
PAT_CORRECT_MARK = re.compile(r"^#\s*")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_blocks(text: str) -> list:
    lines = text.splitlines()
    blocks = []

    STATE_BEFORE_Q   = "before_q"
    STATE_IN_Q       = "in_q"
    STATE_IN_VARIANT = "in_variant"

    state          = STATE_BEFORE_Q
    current        = None
    variant_buf    = []
    variant_correct = False

    def _flush_variant():
        nonlocal variant_buf, variant_correct
        vtext = _clean(" ".join(variant_buf))
        if vtext:
            current["variants"].append({"text": vtext, "correct": variant_correct})
        variant_buf = []
        variant_correct = False

    for raw in lines:
        line = raw.strip()

        if PAT_Q_SEP.match(line):
            if current is not None:
                if state == STATE_IN_VARIANT:
                    _flush_variant()
                blocks.append(current)
            inline_q = PAT_Q_SEP.sub("", line).strip()
            current = {"question": inline_q, "variants": []}
            variant_buf = []
            variant_correct = False
            state = STATE_IN_Q
            continue

        if PAT_V_SEP.match(line):
            if current is None:
                continue
            if state == STATE_IN_VARIANT:
                _flush_variant()
            state = STATE_IN_VARIANT
            continue

        if current is None:
            continue

        if state == STATE_IN_Q:
            if line:
                if current["question"]:
                    current["question"] += " " + line
                else:
                    current["question"] = line
            continue

        if state == STATE_IN_VARIANT:
            if not line:
                continue
            if not variant_buf:
                if PAT_CORRECT_MARK.match(line):
                    variant_correct = True
                    line = PAT_CORRECT_MARK.sub("", line).strip()
            variant_buf.append(line)
            continue

    if current is not None:
        if state == STATE_IN_VARIANT:
            _flush_variant()
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


class PlusPlusConverter(BaseConverter):
    CONVERTER_ID = 10002
    NAME         = "plusplus_hash"
    DESCRIPTION  = "+++/===/# format -> A/B/C/D + ANSWER: X"
    SUPPORTED_EXTENSIONS = {".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls"}
    PRIORITY     = 10

    @classmethod
    def can_handle(cls, text: str) -> bool:
        lines = text.splitlines()
        q_count = sum(1 for l in lines if re.match(r"^\+{3,}", l.strip()))
        v_count = sum(1 for l in lines if re.match(r"^={3,}", l.strip()))
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
