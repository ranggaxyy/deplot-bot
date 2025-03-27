import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Konfigurasi Logging yang Lebih Baik
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Muat variabel environment
load_dotenv()

class BotConfig:
    """Kelas konfigurasi bot"""
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    INACTIVE_RESPONSE = "😴 Bot lagi mode istirahat nih~ Sabar ya, nanti balik lagi!"

# Inisialisasi Bot dengan konfigurasi yang kompatibel dengan aiogram 3.7.0+
bot = Bot(
    token=BotConfig.BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode='HTML')
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

@dp.message()
async def handle_all_messages(message: Message):
    """Handler pesan universal dengan logging minimal"""
    logger.info(f"Pesan dari {message.from_user.username or 'Pengguna'}: {message.text}")
    await message.reply(BotConfig.INACTIVE_RESPONSE)

@dp.callback_query()
async def handle_all_callback_queries(callback: CallbackQuery):
    """Handler callback query universal dengan logging"""
    logger.info(f"Callback dari {callback.from_user.username or 'Pengguna'}")
    await callback.answer(BotConfig.INACTIVE_RESPONSE, show_alert=True)

async def main():
    """Fungsi utama untuk menjalankan bot dengan error handling yang lebih baik"""
    try:
        logger.info("Bot sedang memulai...")
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types()
        )
    except Exception as e:
        logger.error(f"Kesalahan fatal saat menjalankan bot: {e}")
    finally:
        await bot.session.close()
        logger.info("Bot telah berhenti.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot dihentikan secara manual.")