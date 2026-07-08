import asyncio
import logging
import os
import re
import tempfile

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, Message
from yt_dlp import YoutubeDL

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Agar o'z Bot API serverimiz bo'lsa (LOCAL_BOT_API), fayl cheklovi 50 MB -> 2 GB.
_local_api = os.getenv("LOCAL_BOT_API")
if _local_api:
    _session = AiohttpSession(api=TelegramAPIServer.from_base(_local_api))
    bot = Bot(
        os.getenv("BOT_TOKEN"),
        session=_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    MAX_FILE_SIZE = 2000 * 1024 * 1024  # o'z serverimiz: 2 GB gacha
else:
    bot = Bot(os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    MAX_FILE_SIZE = 50 * 1024 * 1024  # standart Telegram cheklovi
dp = Dispatcher()

LINK_PATTERN = re.compile(
    r"(https?://(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com)/\S+)",
    re.IGNORECASE,
)

# YouTube bulut serverlarni bloklaydi ("Sign in to confirm you're not a bot").
# Yonida cookies.txt bo'lsa, uni ishlatib blokdan o'tamiz.
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")


def download_video(url: str, out_dir: str) -> str:
    ydl_opts = {
        "format": (
            "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=720]+bestaudio/"
            "bestvideo+bestaudio/best"
        ),
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "no_warnings": True,
    }
    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Assalomu alaykum! Men Chaqqon Robotman ✅\n\n"
        "Menga YouTube yoki Instagram videosining havolasini yuboring, "
        "men uni siz uchun yuklab beraman.\n\n"
        "Buyruqlar ro'yxati uchun /help ni yuboring."
    )


@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "<b>Qo'llanma</b>\n\n"
        "• YouTube yoki Instagram video havolasini yuboring — video yuklab beraman.\n"
        "• Fayl hajmi 50 MB dan katta bo'lsa, Telegram cheklovi tufayli yubora olmayman.\n"
        "• /start — botni qayta ishga tushirish"
    )


@dp.message(F.text.regexp(LINK_PATTERN))
async def download_handler(message: Message):
    match = LINK_PATTERN.search(message.text)
    url = match.group(1)

    status = await message.answer("⏳ Video yuklanmoqda, biroz kuting...")
    await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            file_path = await asyncio.to_thread(download_video, url, tmp_dir)
        except Exception as e:
            logging.exception("Download failed for %s", url)
            await status.edit_text(f"❌ Videoni yuklab bo'lmadi.\nSabab: {e}")
            return

        if not os.path.exists(file_path):
            await status.edit_text("❌ Video topilmadi yoki formatga mos kelmadi.")
            return

        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            await status.edit_text(
                "❌ Video hajmi 50 MB dan katta, Telegram orqali yubora olmayman."
            )
            return

        try:
            await message.answer_video(FSInputFile(file_path))
            await status.delete()
        except Exception as e:
            logging.exception("Sending video failed")
            await status.edit_text(f"❌ Videoni yuborishda xatolik: {e}")


@dp.message(F.text)
async def fallback_handler(message: Message):
    await message.answer(
        "Men faqat YouTube yoki Instagram video havolalarini tushunaman.\n"
        "Iltimos, to'g'ri havola yuboring yoki /help ni bosing."
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
