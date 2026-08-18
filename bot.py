import asyncio
import logging
import os
import re
import shutil
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
from yt_dlp.version import __version__ as yt_dlp_version

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

# yt-dlp YouTube pleyerining JS kodini yechish uchun JS runtime talab qiladi.
# Usiz ba'zi formatlar umuman ko'rinmaydi. Mavjudlarini topib beramiz.
JS_RUNTIMES = [r for r in ("deno", "node", "bun") if shutil.which(r)]
if not JS_RUNTIMES:
    logging.warning(
        "JS runtime (deno/node/bun) topilmadi - YouTube formatlari topilmasligi mumkin."
    )


# YouTube videoni video va audio oqim sifatida alohida beradi (DASH), ularni
# birlashtirish uchun ffmpeg shart. ffmpeg bo'lmasa faqat bitta faylli
# (progressive) formatni so'raymiz - sifati pastroq, lekin ishlaydi.
HAS_FFMPEG = shutil.which("ffmpeg") is not None

if HAS_FFMPEG:
    VIDEO_FORMAT = (
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
        "bestvideo[height<=720]+bestaudio/"
        "bestvideo+bestaudio/best"
    )
else:
    logging.warning(
        "ffmpeg topilmadi - YouTube videolari faqat past sifatda yuklanadi. "
        "Yaxshi sifat uchun ffmpeg o'rnating."
    )
    VIDEO_FORMAT = (
        "best[ext=mp4][height<=720]/best[ext=mp4]/"
        "best*[vcodec!=none][acodec!=none][height<=720]/"
        "best*[vcodec!=none][acodec!=none]/best"
    )


def download_video(url: str, out_dir: str) -> str:
    ydl_opts = {
        "format": VIDEO_FORMAT,
        "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "no_warnings": True,
    }
    if HAS_FFMPEG:
        ydl_opts["merge_output_format"] = "mp4"
    if JS_RUNTIMES:
        ydl_opts["js_runtimes"] = {name: {} for name in JS_RUNTIMES}
        # JS challenge yechuvchi skriptni yt-dlp ning rasmiy repozitoriysidan
        # olishga ruxsat beramiz - usiz YouTube formatlari topilmaydi.
        ydl_opts["remote_components"] = {"ejs:github"}
    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Birlashtirilgandan keyin haqiqiy fayl nomi prepare_filename() dan
        # farq qilishi mumkin, shuning uchun avval filepath ni olamiz.
        downloads = info.get("requested_downloads") or []
        if downloads and downloads[0].get("filepath"):
            return downloads[0]["filepath"]
        return ydl.prepare_filename(info)


def explain_download_error(error: Exception) -> str:
    """yt-dlp ning inglizcha xatosini foydalanuvchiga tushunarli xabarga aylantiradi."""
    text = str(error).lower()
    if (
        "sign in to confirm" in text
        or "not a bot" in text
        or "no video formats" in text
        or "403" in text
    ):
        return (
            "❌ YouTube bu videoni tekshiruvsiz bermayapti.\n\n"
            "Bot papkasida <code>cookies.txt</code> fayli bo'lishi kerak "
            "(YouTube'ga kirgan brauzerdan eksport qilinadi)."
        )
    if "requested format is not available" in text:
        return (
            "❌ Bu video uchun mos format topilmadi.\n\n"
            "Sabab: YouTube videoni faqat alohida video va audio oqim "
            "sifatida bermoqda. Ularni birlashtirish uchun serverda "
            "<b>ffmpeg</b> o'rnatilgan bo'lishi kerak.\n\n"
            "Holatni tekshirish: /diag"
        )
    if "ffmpeg" in text:
        return "❌ Videoni birlashtirib bo'lmadi: ffmpeg o'rnatilmagan."
    if "private" in text or "unavailable" in text:
        return "❌ Bu video mavjud emas yoki yopiq."
    if "age" in text and "restrict" in text:
        return "❌ Bu videoda yosh cheklovi bor, yuklab bo'lmaydi."
    return f"❌ Videoni yuklab bo'lmadi.\nSabab: {error}"


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
        "• /start — botni qayta ishga tushirish\n"
        "• /diag — texnik holatni tekshirish"
    )


@dp.message(Command("diag"))
async def diag_handler(message: Message):
    """Bot ishlayotgan muhitni ko'rsatadi - nosozlikni topish uchun."""
    ffmpeg_path = shutil.which("ffmpeg")
    lines = [
        "<b>Muhit holati</b>",
        "",
        f"ffmpeg: {'OK - ' + ffmpeg_path if ffmpeg_path else 'topilmadi'}",
        f"JS runtime: {', '.join(JS_RUNTIMES) if JS_RUNTIMES else 'topilmadi'}",
        f"cookies.txt: {'OK' if os.path.exists(COOKIES_FILE) else 'topilmadi'}",
        f"yt-dlp: {yt_dlp_version}",
        "",
        f"Format: <code>{VIDEO_FORMAT}</code>",
    ]
    await message.answer("\n".join(lines))


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
            await status.edit_text(explain_download_error(e))
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
