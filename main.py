"""
main.py — Quiz Format Converter Telegram Bot
---------------------------------------------
Faylni yuborasiz → konvertatsiya qilingan faylni olasiz.

Muhit o'zgaruvchilari (.env yoki Railway Environment Variables):
  BOT_TOKEN  — Telegram bot tokeni (@BotFather dan oling)

Ishga tushirish:
  python main.py
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from telegram import Update, Document
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from router import route, UnsupportedFormatError, NoConverterFoundError
from utils.file_reader import SUPPORTED_EXTENSIONS

# ── Logging sozlamasi ─────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Konfiguratsiya ────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Telegram: bitta faylning maksimal hajmi (20 MB)
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE    = MAX_FILE_SIZE_MB * 1024 * 1024

# Qabul qilinadigan kengaytmalar (foydalanuvchiga ko'rsatish uchun)
ACCEPTED_EXT_STR = "  ".join(sorted(SUPPORTED_EXTENSIONS))


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 *Quiz Format Converter Bot*\n\n"
        "Test faylini yuboring — men uni standart formatga o'tkazib beraman.\n\n"
        "📎 *Qo'llab-quvvatlanadigan formatlar:*\n"
        f"`{ACCEPTED_EXT_STR}`\n\n"
        "📝 *Kirish formati misoli:*\n"
        "```\n"
        "?.Savol matni\n"
        "=Noto'g'ri javob\n"
        "+To'g'ri javob\n"
        "=Noto'g'ri javob\n"
        "```\n\n"
        "📤 *Chiqish formatiga misol:*\n"
        "```\n"
        "1. Savol matni\n\n"
        "    A. Noto'g'ri javob\n"
        "    B. To'g'ri javob\n"
        "    C. Noto'g'ri javob\n\n"
        "    ANSWER: B\n"
        "```\n\n"
        "Faylni yuboring! 🚀"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2.value if False else "Markdown")


# ── /help ─────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "ℹ️ *Yordam*\n\n"
        "1\\. Test faylini shu botga yuboring\n"
        "2\\. Bot faylni qayta ishlaydi\n"
        "3\\. Konvertatsiya qilingan `.txt` faylni olasiz\n\n"
        "*Qo'llab-quvvatlanadigan kirish formatlari:*\n"
        f"`{ACCEPTED_EXT_STR}`\n\n"
        "*Boshqa savol?* — @yourname ga murojaat qiling"
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2")


# ── Fayl qabul qilish ─────────────────────────────────────────────────────────

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi yuborgan faylni qayta ishlash."""
    doc: Document = update.message.document
    user_id   = update.effective_user.id
    user_name = update.effective_user.full_name

    logger.info(f"Fayl keldi: user={user_id} ({user_name}), file={doc.file_name}, size={doc.file_size}")

    # ── Fayl hajmini tekshirish ───────────────────────────────────────────────
    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ Fayl juda katta ({doc.file_size // (1024*1024)} MB).\n"
            f"Maksimal hajm: {MAX_FILE_SIZE_MB} MB."
        )
        return

    # ── Kengaytmani tekshirish (erta chiqish) ─────────────────────────────────
    file_ext = Path(doc.file_name or "").suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        await update.message.reply_text(
            f"❌ `{file_ext}` formati qo'llab-quvvatlanmaydi.\n\n"
            f"Yuborishingiz mumkin bo'lgan formatlar:\n"
            f"`{ACCEPTED_EXT_STR}`",
            parse_mode="Markdown"
        )
        return

    # ── "Qayta ishlanmoqda..." xabari ────────────────────────────────────────
    status_msg = await update.message.reply_text("⏳ Qayta ishlanmoqda...")

    # ── Faylni vaqtinchalik papkaga yuklash ──────────────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path  = Path(tmpdir) / (doc.file_name or f"upload{file_ext}")
        output_path = Path(tmpdir) / f"{input_path.stem}_converted.txt"

        try:
            tg_file = await context.bot.get_file(doc.file_id)
            await tg_file.download_to_drive(str(input_path))
        except Exception as e:
            logger.error(f"Yuklab bo'lmadi: {e}")
            await status_msg.edit_text("❌ Faylni yuklab bo'lmadi. Qaytadan urinib ko'ring.")
            return

        # ── Konvertatsiya ─────────────────────────────────────────────────────
        try:
            result = route(str(input_path))
        except UnsupportedFormatError as e:
            await status_msg.edit_text(f"❌ {e}")
            return
        except NoConverterFoundError as e:
            await status_msg.edit_text(
                f"⚠️ Fayl formati tanilmadi.\n\n{e}\n\n"
                "Fayl to'g'ri formatdami? /help ni ko'ring."
            )
            return
        except ImportError as e:
            logger.error(f"Kutubxona xatosi: {e}")
            await status_msg.edit_text(
                f"⚙️ Server xatosi: kerakli kutubxona o'rnatilmagan.\n`{e}`",
                parse_mode="Markdown"
            )
            return
        except Exception as e:
            logger.exception(f"Kutilmagan xato: {e}")
            await status_msg.edit_text(f"❌ Kutilmagan xato yuz berdi: {e}")
            return

        # ── Natijani tekshirish ───────────────────────────────────────────────
        if not result.success or not result.output_text.strip():
            error_detail = "\n".join(f"• {e}" for e in result.errors[:5])
            await status_msg.edit_text(
                f"⚠️ Konvertatsiya qilingan savollar topilmadi.\n\n"
                f"Xatoliklar:\n{error_detail or 'Noma'lum sabab'}"
            )
            return

        # ── Natija faylini saqlash va yuborish ───────────────────────────────
        output_path.write_text(result.output_text, encoding="utf-8")

        # Xulosa xabari
        summary = _build_summary(doc.file_name, result)

        await status_msg.delete()
        await update.message.reply_document(
            document=output_path.open("rb"),
            filename=output_path.name,
            caption=summary,
            parse_mode="Markdown"
        )

        logger.info(
            f"Yuborildi: user={user_id}, converted={result.converted_count}, "
            f"skipped={result.skipped_count}, converter={result.converter_name}"
        )


def _build_summary(filename: str, result) -> str:
    """Natija xabarini qurish."""
    lines = [
        f"✅ *{filename}* konvertatsiya qilindi\n",
        f"📊 Savollar : *{result.converted_count}* ta",
    ]
    if result.skipped_count:
        lines.append(f"⚠️ O'tkazildi: *{result.skipped_count}* ta")

    if result.errors:
        lines.append("\n*Ogohlantirmalar:*")
        for e in result.errors[:5]:
            lines.append(f"  `{e[:80]}`")
        if len(result.errors) > 5:
            lines.append(f"  _...va yana {len(result.errors)-5} ta_")

    return "\n".join(lines)


# ── Noto'g'ri xabar ───────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📎 Iltimos, fayl yuboring.\n"
        f"Qabul qilinadigan formatlar: `{ACCEPTED_EXT_STR}`",
        parse_mode="Markdown"
    )


# ── Ishga tushirish ───────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!\n"
            "Railway dashboard → Variables → BOT_TOKEN = <tokeningiz>"
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot ishga tushdi 🤖")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
