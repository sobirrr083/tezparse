"""
main.py
--------
Quiz Format Converter Telegram Bot.

Muhit ozgaruvchilari:
  BOT_TOKEN — Telegram bot tokeni (@BotFather)
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

from router import route, UnsupportedFormatError, NoConverterFoundError
from utils.file_reader import SUPPORTED_EXTENSIONS

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE    = MAX_FILE_SIZE_MB * 1024 * 1024
ACCEPTED_EXT_STR = "  ".join(sorted(SUPPORTED_EXTENSIONS))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Quiz Format Converter Bot\n\n"
        "Test faylini yuboring - konvertatsiya qilib beraman.\n\n"
        "Qabul qilinadigan formatlar:\n"
        f"{ACCEPTED_EXT_STR}\n\n"
        "Kirish formati:\n"
        "?.Savol matni\n"
        "=Notogri javob\n"
        "+Togri javob\n"
        "=Notogri javob\n\n"
        "Chiqish formati:\n"
        "1. Savol matni\n"
        "    A. Notogri javob\n"
        "    B. Togri javob\n"
        "    ANSWER: B"
    )
    await update.message.reply_text(text)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Yordam:\n\n"
        "1. Test faylini shu botga yuboring\n"
        "2. Bot faylni qayta ishlaydi\n"
        "3. Konvertatsiya qilingan .txt faylni olasiz\n\n"
        f"Qabul qilinadigan formatlar: {ACCEPTED_EXT_STR}"
    )
    await update.message.reply_text(text)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc: Document = update.message.document
    user_id   = update.effective_user.id
    user_name = update.effective_user.full_name

    logger.info(f"Fayl keldi: user={user_id} ({user_name}), file={doc.file_name}, size={doc.file_size}")

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"Fayl juda katta ({doc.file_size // (1024*1024)} MB). "
            f"Maksimal: {MAX_FILE_SIZE_MB} MB."
        )
        return

    file_ext = Path(doc.file_name or "").suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        await update.message.reply_text(
            f"'{file_ext}' formati qabul qilinmaydi.\n"
            f"Yuborishingiz mumkin: {ACCEPTED_EXT_STR}"
        )
        return

    status_msg = await update.message.reply_text("Qayta ishlanmoqda...")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path  = Path(tmpdir) / (doc.file_name or f"upload{file_ext}")
        output_path = Path(tmpdir) / f"{input_path.stem}_converted.txt"

        try:
            tg_file = await context.bot.get_file(doc.file_id)
            await tg_file.download_to_drive(str(input_path))
        except Exception as e:
            logger.error(f"Yuklab bolmadi: {e}")
            await status_msg.edit_text("Faylni yuklab bolmadi. Qaytadan urinib koring.")
            return

        try:
            result = route(str(input_path))
        except UnsupportedFormatError as e:
            await status_msg.edit_text(str(e))
            return
        except NoConverterFoundError as e:
            await status_msg.edit_text(
                f"Fayl formati tanilmadi.\n\n{e}\n\nFayl togri formatdami? /help"
            )
            return
        except ImportError as e:
            logger.error(f"Kutubxona xatosi: {e}")
            await status_msg.edit_text(f"Server xatosi: kerakli kutubxona yoq.\n{e}")
            return
        except Exception as e:
            logger.exception(f"Kutilmagan xato: {e}")
            await status_msg.edit_text(f"Kutilmagan xato: {e}")
            return

        if not result.success or not result.output_text.strip():
            error_detail = "\n".join(f"- {e}" for e in result.errors[:5])
            fallback = "Noma'lum sabab"
            await status_msg.edit_text(
                f"Konvertatsiya qilingan savollar topilmadi.\n\n"
                f"Xatoliklar:\n{error_detail or fallback}"
            )
            return

        output_path.write_text(result.output_text, encoding="utf-8")

        summary_lines = [
            f"{doc.file_name} konvertatsiya qilindi",
            f"Savollar: {result.converted_count} ta",
        ]
        if result.skipped_count:
            summary_lines.append(f"Otkazildi: {result.skipped_count} ta")
        if result.errors:
            summary_lines.append("\nOgohlantirmalar:")
            for e in result.errors[:5]:
                summary_lines.append(f"  {e[:80]}")
        summary = "\n".join(summary_lines)

        await status_msg.delete()
        await update.message.reply_document(
            document=output_path.open("rb"),
            filename=output_path.name,
            caption=summary,
        )

        logger.info(
            f"Yuborildi: user={user_id}, id={result.converter_id}, "
            f"converted={result.converted_count}, skipped={result.skipped_count}"
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Fayl yuboring.\nQabul qilinadigan formatlar: {ACCEPTED_EXT_STR}"
    )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN muhit ozgaruvchisi ornitirilmagan!\n"
            "Railway: Variables -> BOT_TOKEN = tokeningiz"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot ishga tushdi")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
