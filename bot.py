import asyncio
import logging
import random
import os
from typing import Dict, List
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from dotenv import load_dotenv
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Inisialisasi bot dengan token dari environment variable
TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Manajemen anti-cheat dan rate limiting
class UserManager:
    def __init__(self):
        self.user_attempts = {}  # Melacak percobaan game per pengguna
        self.user_cooldowns = {}  # Mengatur cooldown antar game
        self.global_game_limits = {
            'max_daily_games': 20,  # Maksimal game per hari
            'max_consecutive_attempts': 5  # Maksimal percobaan berturut-turut
        }

    def check_user_game_limit(self, user_id: int) -> bool:
        """Memeriksa apakah pengguna melebihi batas harian"""
        user_data = self.user_attempts.get(user_id, {})
        today = datetime.now().date()
        today_games = user_data.get(today, 0)
        return today_games < self.global_game_limits['max_daily_games']

    def record_game_attempt(self, user_id: int):
        """Mencatat percobaan game"""
        today = datetime.now().date()
        if user_id not in self.user_attempts:
            self.user_attempts[user_id] = {}
        
        user_data = self.user_attempts[user_id]
        user_data[today] = user_data.get(today, 0) + 1

    def check_cooldown(self, user_id: int) -> bool:
        """Memeriksa cooldown antar game"""
        current_time = datetime.now()
        if user_id in self.user_cooldowns:
            last_game_time = self.user_cooldowns[user_id]
            if (current_time - last_game_time).total_seconds() < 10:  # 10 detik cooldown
                return False
        
        self.user_cooldowns[user_id] = current_time
        return True

    def check_consecutive_attempts(self, user_id: int, game_type: str) -> bool:
        """Memeriksa percobaan berturut-turut"""
        if not hasattr(self, '_consecutive_attempts'):
            self._consecutive_attempts = {}
        
        if user_id not in self._consecutive_attempts:
            self._consecutive_attempts[user_id] = {}
        
        user_attempts = self._consecutive_attempts[user_id]
        current_time = datetime.now()
        
        # Reset jika sudah lama
        if game_type not in user_attempts or \
           (current_time - user_attempts.get(f'{game_type}_time', current_time)).total_seconds() > 60:
            user_attempts[game_type] = 1
            user_attempts[f'{game_type}_time'] = current_time
            return True
        
        user_attempts[game_type] += 1
        user_attempts[f'{game_type}_time'] = current_time
        
        return user_attempts[game_type] <= self.global_game_limits['max_consecutive_attempts']

# State untuk mengatur alur permainan
class GameStates(StatesGroup):
    MAIN_MENU = State()
    MATH_GAME = State()
    WORD_RIDDLE = State()
    LOGIC_CHALLENGE = State()

# Inisialisasi user manager
user_manager = UserManager()

# Daftar pertanyaan dengan tingkat kesulitan - DIPERBAIKI
MATH_QUESTIONS = [
    {"text": "8 x 7 = ?", "answer": "56", "difficulty": 1},
    {"text": "100 - 37 = ?", "answer": "63", "difficulty": 1},
    {"text": "12 x 9 = ?", "answer": "108", "difficulty": 2},
    {"text": "144 ÷ 12 = ?", "answer": "12", "difficulty": 2},
    {"text": "25 + 37 = ?", "answer": "62", "difficulty": 1},
    {"text": "(15 x 4) - 22 = ?", "answer": "38", "difficulty": 3},
    {"text": "64 ÷ 8 + 7 = ?", "answer": "15", "difficulty": 3}
]

WORD_RIDDLES = [
    {"text": "Apa yang selalu naik tapi tidak pernah turun?", "answer": "umur", "difficulty": 1},
    {"text": "Semakin banyak dikurangi, semakin besar?", "answer": "lubang", "difficulty": 2},
    {"text": "Berkaki empat, tidak bernyawa, bisa bergerak?", "answer": "meja", "difficulty": 1},
    {"text": "Apa yang bisa mendengar tapi tidak punya telinga?", "answer": "angin", "difficulty": 3},
    {"text": "Semakin diamati semakin hilang?", "answer": "bintang", "difficulty": 3}
]

LOGIC_CHALLENGES = [
    {
        "text": "Ada 3 kotak. Satu kotak berisi emas, satu berisi perak, dan satu kosong. "
        "Label di masing-masing kotak salah. Di kotak emas tertulis 'Emas', "
        "di kotak perak tertulis 'Kosong', dan di kotak kosong tertulis 'Perak'. "
        "Kotak mana yang berisi emas?",
        "answer": "kotak perak", 
        "difficulty": 3
    },
    {
        "text": "Seorang ayah berkata pada anaknya: 'Umurku sekarang adalah 4 kali umurmu. "
        "5 tahun lagi, umurku akan menjadi 3 kali umurmu'. Berapa umur ayah dan anak sekarang?",
        "answer": "ayah 40 tahun, anak 10 tahun", 
        "difficulty": 3
    }
]

def create_main_menu_keyboard():
    """Membuat keyboard menu utama"""
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="🧮 Kuis Matematika")
    keyboard.button(text="🤔 Tebak Kata")
    keyboard.button(text="🧠 Tantangan Logika")
    keyboard.button(text="📊 Statistik")
    keyboard.button(text="❓ Bantuan")
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)

def create_back_to_menu_keyboard():
    """Membuat keyboard kembali ke menu"""
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="🏠 Kembali ke Menu Utama")
    return keyboard.as_markup(resize_keyboard=True)

def create_help_text():
    return (
        "*🤖 Panduan Bot Game Pengasah Otak 🤖*\n\n"
        "*Anti-Cheat Features:*\n"
        "• Maksimal *20 game per hari*\n"
        "• *Cooldown 10 detik* antar game\n"
        "• Maksimal *5 percobaan berturut-turut*\n\n"
        "*Tersedia 3 jenis permainan:*\n"
        "1. 🧮 *Kuis Matematika*: Uji kemampuan matematikamu!\n"
        "2. 🤔 *Tebak Kata*: Selesaikan teka-teki lucu!\n"
        "3. 🧠 *Tantangan Logika*: Asah logika dan nalarmu!\n\n"
        "*Aturan Umum:*\n"
        "• Kamu punya *3 kesempatan* untuk menjawab setiap soal\n"
        "• Jawab dengan tepat untuk menang\n"
        "• Kamu bisa kembali ke menu utama kapan saja"
    )

@dp.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    """Handler untuk command /start"""
    await state.set_state(GameStates.MAIN_MENU)
    await message.answer(
        "*Selamat datang di Bot Game Pengasah Otak! 🧠*\n\n"
        "Ayo latih kemampuan berpikirmu dengan berbagai tantangan menarik. "
        "Pilih salah satu permainan atau tekan tombol *Bantuan* untuk informasi lebih lanjut.",
        parse_mode="Markdown",
        reply_markup=create_main_menu_keyboard()
    )

@dp.message(GameStates.MAIN_MENU, F.text == "❓ Bantuan")
async def show_help(message: Message):
    """Menampilkan panduan penggunaan bot"""
    await message.answer(
        create_help_text(), 
        parse_mode="Markdown",
        reply_markup=create_main_menu_keyboard()
    )

@dp.message(GameStates.MAIN_MENU, F.text == "📊 Statistik")
async def show_stats(message: Message):
    """Menampilkan statistik sederhana"""
    user_id = message.from_user.id
    user_data = user_manager.user_attempts.get(user_id, {})
    
    today = datetime.now().date()
    today_games = user_data.get(today, 0)
    
    stats_text = (
        "*📊 Statistik Permainan*\n"
        f"• *Total Game Hari Ini*: {today_games}\n"
        "• *Catatan*: Statistik lengkap akan dikembangkan!"
    )
    await message.answer(
        stats_text, 
        parse_mode="Markdown",
        reply_markup=create_main_menu_keyboard()
    )

def select_game_question(questions: List[dict], difficulty: int = None) -> dict:
    """Memilih pertanyaan berdasarkan tingkat kesulitan"""
    if difficulty:
        difficulty_questions = [q for q in questions if q['difficulty'] == difficulty]
        return random.choice(difficulty_questions) if difficulty_questions else random.choice(questions)
    return random.choice(questions)

async def start_game(message: Message, state: FSMContext, game_type: str, questions: List[dict]):
    """Fungsi umum untuk memulai game"""
    user_id = message.from_user.id

    # Cek cooldown
    if not user_manager.check_cooldown(user_id):
        await message.answer(
            "*⏳ Peringatan:* Tunggu sebentar sebelum memulai game baru!",
            parse_mode="Markdown"
        )
        return

    # Cek batas game harian
    if not user_manager.check_user_game_limit(user_id):
        await message.answer(
            "*🚫 Batas Harian Tercapai*\n"
            "Kamu sudah mencapai maksimal game hari ini. Coba lagi besok!",
            parse_mode="Markdown"
        )
        return

    # Cek percobaan berturut-turut
    if not user_manager.check_consecutive_attempts(user_id, game_type):
        await message.answer(
            "*⚠️ Peringatan:* Terlalu banyak percobaan berturut-turut!",
            parse_mode="Markdown"
        )
        return

    # Pilih pertanyaan
    question = select_game_question(questions)
    
    # Set state game
    state_map = {
        "math": GameStates.MATH_GAME,
        "riddle": GameStates.WORD_RIDDLE,
        "logic": GameStates.LOGIC_CHALLENGE
    }
    await state.set_state(state_map[game_type])
    
    # Catat percobaan
    user_manager.record_game_attempt(user_id)
    
    # Update state
    await state.update_data(
        current_question=question,
        attempts=0,
        game_type=game_type
    )

    # Kirim pertanyaan
    game_info = {
        "math": ("*🧮 Kuis Matematika*", "Hitung"),
        "riddle": ("*🤔 Tebak Kata*", "Tebak"),
        "logic": ("*🧠 Tantangan Logika*", "Selesaikan")
    }
    
    title, prompt = game_info[game_type]
    await message.answer(
        f"{title}\n\n"
        f"*{prompt}*: `{question['text']}`\n\n"
        "Tuliskan jawabanmu!",
        parse_mode="Markdown",
        reply_markup=create_back_to_menu_keyboard()
    )

@dp.message(GameStates.MAIN_MENU, F.text == "🧮 Kuis Matematika")
async def start_math_quiz(message: Message, state: FSMContext):
    """Memulai kuis matematika"""
    await start_game(message, state, "math", MATH_QUESTIONS)

@dp.message(GameStates.MAIN_MENU, F.text == "🤔 Tebak Kata")
async def start_word_riddle(message: Message, state: FSMContext):
    """Memulai tebak kata"""
    await start_game(message, state, "riddle", WORD_RIDDLES)

@dp.message(GameStates.MAIN_MENU, F.text == "🧠 Tantangan Logika")
async def start_logic_challenge(message: Message, state: FSMContext):
    """Memulai tantangan logika"""
    await start_game(message, state, "logic", LOGIC_CHALLENGES)

@dp.message(GameStates.MATH_GAME)
@dp.message(GameStates.WORD_RIDDLE)
@dp.message(GameStates.LOGIC_CHALLENGE)
async def handle_game_answer(message: Message, state: FSMContext):
    """Handler untuk menjawab pertanyaan di berbagai game"""
    # Cek apakah ingin kembali ke menu
    if message.text == "🏠 Kembali ke Menu Utama":
        await state.set_state(GameStates.MAIN_MENU)
        await message.answer(
            "Anda telah keluar dari permainan.",
            reply_markup=create_main_menu_keyboard()
        )
        return

    # Ambil data state saat ini
    current_state = await state.get_state()
    data = await state.get_data()
    
    user_answer = message.text.lower().strip()
    current_question = data['current_question']
    attempts = data.get('attempts', 0)
    game_type = data.get('game_type', '')

    # Tentukan game dan jawaban berdasarkan state
    game_map = {
        GameStates.MATH_GAME: ("Kuis Matematika", MATH_QUESTIONS),
        GameStates.WORD_RIDDLE: ("Tebak Kata", WORD_RIDDLES),
        GameStates.LOGIC_CHALLENGE: ("Tantangan Logika", LOGIC_CHALLENGES)
    }
    
    game_name, game_questions = game_map.get(current_state, ("Game", []))
    correct_answer = current_question['answer'].lower()

    attempts += 1

    if user_answer == correct_answer:
        await message.answer(
            f"*✅ Selamat!* Jawabanmu benar dalam *{attempts} percobaan*. "
            f"Kamu hebat dalam *{game_name}*!",
            parse_mode="Markdown",
            reply_markup=create_main_menu_keyboard()
        )
        await state.set_state(GameStates.MAIN_MENU)
    elif attempts >= 3:
        await message.answer(
            f"*❌ Maaf, kesempatan habis.*\n"
            f"Jawaban yang benar adalah: `{correct_answer}`\n"
            f"Jangan menyerah! Coba lagi di *{game_name}*.",
            parse_mode="Markdown",
            reply_markup=create_main_menu_keyboard()
        )
        await state.set_state(GameStates.MAIN_MENU)
    else:
        attempts_left = 3 - attempts
        await state.update_data(attempts=attempts)
        await message.answer(
            f"*❌ Salah!* Kamu punya *{attempts_left} kesempatan* lagi dalam *{game_name}*.",
            parse_mode="Markdown",
            reply_markup=create_back_to_menu_keyboard()
        )

async def main():
    """Fungsi utama untuk menjalankan bot"""
    logger.info("Starting Bot")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# Requirements untuk bot
# aiogram==3.19.0
# python-dotenv  # Untuk memuat environment variables