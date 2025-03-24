import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Bot token dari BotFather
TOKEN = os.getenv("BOT_TOKEN")

# Inisialisasi router
router = Router()

# States untuk form
class Form(StatesGroup):
    name = State()
    age = State()
    gender = State()

# Keyboard inline untuk gender
gender_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Laki-laki", callback_data="gender:male"),
            InlineKeyboardButton(text="Perempuan", callback_data="gender:female"),
        ]
    ]
)

# Command /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Selamat datang di Bot Survey!\n"
        "Gunakan /form untuk memulai survey\n"
        "Gunakan /help untuk bantuan"
    )

# Command /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
    Daftar perintah yang tersedia:
    /start - Memulai bot
    /help - Menampilkan bantuan
    /form - Mulai mengisi formulir
    /cancel - Batalkan pengisian formulir
    """
    await message.answer(help_text)

# Command /form - memulai survey
@router.message(Command("form"))
async def cmd_form(message: Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer("Mari mulai survey. Siapa nama Anda?")

# Command /cancel - batalkan pengisian form
@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Tidak ada survey yang sedang berlangsung.")
        return
    
    await state.clear()
    await message.answer("Survey dibatalkan.")

# Handler untuk menerima nama
@router.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.age)
    await message.answer("Berapa umur Anda?")

# Handler untuk menerima umur
@router.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    # Cek apakah input adalah angka
    if not message.text.isdigit():
        await message.answer("Mohon masukkan angka untuk umur Anda.")
        return
    
    await state.update_data(age=int(message.text))
    await state.set_state(Form.gender)
    await message.answer("Pilih jenis kelamin Anda:", reply_markup=gender_keyboard)

# Handler untuk callback dari tombol gender
@router.callback_query(Form.gender, F.data.startswith("gender:"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    gender_value = callback.data.split(":")[1]
    await state.update_data(gender=gender_value)
    
    # Dapatkan semua data yang sudah dikumpulkan
    data = await state.get_data()
    
    # Tampilkan ringkasan data
    await callback.message.answer(
        f"Terima kasih atas partisipasi Anda!\n\n"
        f"Data yang Anda berikan:\n"
        f"Nama: {data['name']}\n"
        f"Umur: {data['age']}\n"
        f"Gender: {'Laki-laki' if data['gender'] == 'male' else 'Perempuan'}"
    )
    
    # Reset state
    await state.clear()
    await callback.answer()

# Handler untuk pesan lainnya ketika tidak dalam state apapun
@router.message(StateFilter(None))
async def echo(message: Message):
    await message.answer(
        "Saya tidak mengerti pesan Anda. Gunakan /help untuk melihat perintah yang tersedia."
    )

async def main() -> None:
    # Inisialisasi Bot instance
    bot = Bot(token=TOKEN)
    
    # Dispatcher dengan memory storage
    dp = Dispatcher(storage=MemoryStorage())
    
    # Daftarkan router
    dp.include_router(router)

    # Hapus webhook terlebih dahulu
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())