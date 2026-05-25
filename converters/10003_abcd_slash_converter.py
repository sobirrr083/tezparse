"""
converters/10003_abcd_slash_converter.py
-----------------------------------------
A/B/C/D variantli, // bilan togri javob belgilangan
formatni standart A/B/C/D + ANSWER: X ga otkazadi.

FORMAT QOIDALARI:
  - Savol: raqam bilan (1. yoki 1)) yoki raqamsiz oddiy matn
  - Variantlar: A) B) C) D) ...  yoki  A. B. C. D. ...
  - Togri javob varianti //  bilan boshlanadi: //B) yoki // B)

MISOL KIRISH:
  1. Savol matni?
  A) Birinchi
  B) Ikkinchi
  //C) Uchinchi  ← togri javob
  D) Tortinchi

  Raqamsiz savol ham ishlaydi
  //A) Togri
  B) Notogri
  C) Notogri

MISOL CHIQISH:
  1. Savol matni?
      A. Birinchi
      B. Ikkinchi
      C. Uchinchi
      D. Tortinchi
      ANSWER: C
"""

import re
from .base import BaseConverter, ConversionResult

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ── Regex ─────────────────────────────────────────────────────────────────────

# Savol: ixtiyoriy "1." yoki "1)" prefiksi bilan yoki unda ham yoq
# Variant liniyasi BOSHIDA bulmaydi (A) bilan boshlanmaydi)
PAT_QUESTION = re.compile(
    r"^\s*"
    r"(?:\d+\s*[.)]\s*)?"   # ixtiyoriy raqam: "1. " "2) " "10. "
    r"([^\s/A-Za-z].+|[A-Z]{2,}.+)",  # savol matni (bitta harf+) emas
    re.DOTALL,
)

# Variant: oldinida "//" bolishi mumkin (togri), keyin A) yoki A.
PAT_VARIANT = re.compile(
    r"^\s*"
    r"(//\s*)?"              # ixtiyoriy "//" — togri javob belgisi
    r"([A-Za-z])\s*[.)]\s*" # harf + nuqta yoki qavs
    r"(.*)",                 # variant matni
    re.DOTALL,
)

# Faqat savol raqami qatori: "1." "2)" — matn yoq (keyingi qatorda savol)
PAT_Q_NUM_ONLY = re.compile(r"^\s*\d+\s*[.)]\s*$")


def _is_variant_line(line: str) -> bool:
    """Qator variant satrimі?"""
    return bool(PAT_VARIANT.match(line))


def _is_question_start(line: str, next_lines: list) -> bool:
    """
    Qator yangi savol boshlanishimi?
    Variant belgisi (A) B) C) D)) bulmagan har qanday tolik qator savol.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if _is_variant_line(stripped):
        return False
    # Raqamli savol: "1. Matn" yoki "1)"
    if re.match(r"^\d+\s*[.)]\s*\S", stripped):
        return True
    # Raqamsiz: agar keyingi qatorlarda variant bor bo'lsa — bu savol
    if next_lines:
        for nl in next_lines[:5]:
            if _is_variant_line(nl.strip()):
                return True
    return False


def _parse_blocks(text: str) -> list:
    lines = text.splitlines()
    blocks = []
    current = None

    i = 0
    while i < len(lines):
        raw  = lines[i]
        line = raw.strip()
        i   += 1

        if not line:
            continue

        mv = PAT_VARIANT.match(line)

        # ── Variant qatori ───────────────────────────────────────────────────
        if mv:
            if current is None:
                # Variant keldi lekin savol yoq — oldingi kontekstga ulantiramiz
                # (bu holat odatda bolmaydi, lekin himoya uchun)
                continue
            is_correct   = bool(mv.group(1))          # "//" bor
            variant_text = mv.group(3).strip()
            # Variant matni keyingi qatorlarda davom etishi mumkin
            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt:
                    break
                if _is_variant_line(nxt):
                    break
                if re.match(r"^\d+\s*[.)]\s*\S", nxt):
                    break
                # Davomi
                variant_text += " " + nxt
                i += 1
            current["variants"].append({
                "text":    _clean(variant_text),
                "correct": is_correct,
            })
            continue

        # ── Savol qatori ─────────────────────────────────────────────────────
        # Raqamli savol
        mq_num = re.match(r"^\s*(\d+)\s*[.)]\s*(.*)", line)
        if mq_num:
            if current is not None:
                blocks.append(current)
            q_text = mq_num.group(2).strip()
            current = {"question": q_text, "variants": []}
            # Savol matni keyingi qatorlarda davom etishi mumkin
            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt:
                    break
                if _is_variant_line(nxt):
                    break
                if re.match(r"^\d+\s*[.)]\s*\S", nxt):
                    break
                current["question"] += " " + nxt
                i += 1
            continue

        # Raqamsiz savol — keyingi qatorda variant bor bo'lsa
        is_q = False
        remaining = lines[i:i+6]
        for nl in remaining:
            if _is_variant_line(nl.strip()):
                is_q = True
                break

        if is_q:
            if current is not None:
                blocks.append(current)
            current = {"question": _clean(line), "variants": []}
            # Savol davomi (keyingisi variant emas bo'lsa)
            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt:
                    break
                if _is_variant_line(nxt):
                    break
                if re.match(r"^\d+\s*[.)]\s*\S", nxt):
                    break
                current["question"] += " " + nxt
                i += 1
            continue

        # Hech narsaga ulanmagan qator — oxirgi savolga yoki variantga ulash
        if current is not None:
            if current["variants"]:
                current["variants"][-1]["text"] += " " + line
            else:
                current["question"] += " " + line

    if current is not None:
        blocks.append(current)

    return blocks


def _clean(text: str) -> str:
    # "//" qoldiqlari tozalash (ehtiyot uchun)
    text = re.sub(r"^//\s*", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


class AbcdSlashConverter(BaseConverter):
    CONVERTER_ID = 10003
    NAME         = "abcd_slash"
    DESCRIPTION  = "A/B/C/D + // togri javob belgisi -> standart format"
    SUPPORTED_EXTENSIONS = {".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls"}
    PRIORITY     = 20   # ?/=//+ dan OLDIN tekshiriladi (yuqori prioritet)

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        // belgisi variant qatorida bor va A)/B)/C)/D) variantlar mavjud.
        """
        lines = text.splitlines()
        has_slash_variant = any(
            re.match(r"^\s*//\s*[A-Za-z]\s*[.)]", l) for l in lines
        )
        has_variants = sum(
            1 for l in lines if re.match(r"^\s*(?://\s*)?[A-Za-z]\s*[.)]\s*\S", l)
        )
        return has_slash_variant and has_variants >= 2

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
