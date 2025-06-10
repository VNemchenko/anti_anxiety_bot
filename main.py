import json
import os
from datetime import datetime, time
from aiogram import Bot, Dispatcher, executor, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from random import choice
from fpdf import FPDF
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

API_TOKEN = os.getenv("BOT_TOKEN")  # Установи переменную окружения

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

pending_timezone = set()

DATA_FILE = "users_data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

EXPLANATION_TEXT = (
    "🔍 Пояснения и примеры\n\n"
    "1. Дыхание. Сделай 5 циклов: вдох через нос на 4 секунды, затем пауза на 4 секунды и медленный выдох через рот на 6 секунд. Такое дыхание помогает снять напряжение.\n"
    "2. Вопрос о действии. Сконцентрируйся на мысли: 'Что я могу сделать сегодня, даже чувствуя тревогу?' — так мозг ищет пути, а не оправдания.\n"
    "3. Маленький шаг. Выбери действие на 5–10 минут: например, навести порядок на столе, сделать короткую зарядку или написать одно письмо.\n\n"
    "Вечерняя практика:\n"
    "1. Выгрузка мыслей. Заведи заметку или блокнот и в течение пяти минут без цензуры записывай всё, что приходит в голову.\n"
    "2. Разбор. Просмотри записи и отметь, какие требуют действий, а какие можно отпустить. Составь план для важных пунктов.\n"
    "3. Благодарность. Закрепи результат парой слов благодарности себе за старания в течение дня."
)

@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"days": {}, "start_date": get_today(), "timezone_offset": 0}
        save_data(data)
    await message.answer(
        "👋 Добро пожаловать в 30-дневную анти-тревожную программу! Каждый день я буду давать тебе задания. Напиши /today чтобы начать.\n\n"
        "Если хочешь получать напоминания по своему времени — напиши /set_timezone и следуй инструкции или укажи смещение сразу: /set_timezone +3."
    )


@dp.message_handler(commands=["menu"])
async def show_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("/today"))
    keyboard.add(KeyboardButton("/stats"), KeyboardButton("/export"))
    keyboard.add(KeyboardButton("/panic"))
    keyboard.add(KeyboardButton("/set_timezone"))
    await message.answer("Выберите команду:", reply_markup=keyboard)


@dp.message_handler(commands=["hide_menu"])
async def hide_menu(message: types.Message):
    await message.answer(
        "Меню скрыто. Чтобы открыть его снова, напишите /menu.",
        reply_markup=ReplyKeyboardRemove(),
    )

@dp.message_handler(commands=["set_timezone"])
async def set_timezone(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    parts = message.text.strip().split()
    if len(parts) != 2:
        pending_timezone.add(user_id)
        await message.answer(
            "Укажи смещение относительно UTC, например +3 или -5"
        )
        return
    try:
        offset = int(parts[1])
    except ValueError:
        await message.answer("⚠️ Неверный формат. Пример: /set_timezone +2")
        return
    data.setdefault(user_id, {"days": {}, "start_date": get_today()})
    data[user_id]["timezone_offset"] = offset
    save_data(data)
    schedule_daily_tasks()
    pending_timezone.discard(user_id)
    await message.answer(f"🕒 Часовой пояс установлен: UTC{offset:+d}")


@dp.message_handler(lambda message: str(message.from_user.id) in pending_timezone)
async def process_timezone_input(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    try:
        offset = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Нужно указать число, например +2 или -4")
        return
    data.setdefault(user_id, {"days": {}, "start_date": get_today()})
    data[user_id]["timezone_offset"] = offset
    save_data(data)
    schedule_daily_tasks()
    pending_timezone.discard(user_id)
    await message.answer(f"🕒 Часовой пояс установлен: UTC{offset:+d}")

@dp.message_handler(commands=["today"])
async def today_task(message: types.Message):
    user_id = str(message.from_user.id)
    today = get_today()
    data = load_data()
    data.setdefault(user_id, {"days": {}, "start_date": today})
    if today not in data[user_id]["days"]:
        data[user_id]["days"][today] = {"morning": False, "evening": False}
        save_data(data)

    text = (
        f"📅 День: {today}\n\n"
        "🧘 Утро:\n"
        "1. Подыши 5 раз: вдох 4с — пауза 4с — выдох 6с.\n"
        "2. Спроси себя: что я могу сделать сегодня несмотря на тревогу?\n"
        "3. Сделай маленький шаг — короткое действие, которое продвинет вперёд.\n\n"
        "🌙 Вечер:\n"
        "1. Пять минут выписывай все мысли в заметку или блокнот.\n"
        "2. Отметь, что требует действий, а что просто шум.\n"
        "3. Поблагодари себя.\n\n"
        "Нажми \"🔍 Пояснение и примеры\" для деталей.\n"
        "Напиши /done_morning или /done_evening по мере выполнения."
    )
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔍 Пояснение и примеры", callback_data="explain_today")
    )
    await message.answer(text, reply_markup=keyboard)

@dp.message_handler(commands=["done_morning"])
async def done_morning(message: types.Message):
    user_id = str(message.from_user.id)
    today = get_today()
    data = load_data()
    data.setdefault(user_id, {"days": {}, "start_date": today})
    data[user_id]["days"].setdefault(today, {})["morning"] = True
    save_data(data)
    await message.answer("✅ Утреннее задание выполнено. Хорошее начало дня!")

@dp.message_handler(commands=["done_evening"])
async def done_evening(message: types.Message):
    user_id = str(message.from_user.id)
    today = get_today()
    data = load_data()
    data.setdefault(user_id, {"days": {}, "start_date": today})
    data[user_id]["days"].setdefault(today, {})["evening"] = True
    save_data(data)
    await message.answer("🌙 Вечернее задание выполнено. Спокойной ночи!")

@dp.message_handler(commands=["stats"])
async def show_stats(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    days = data.get(user_id, {}).get("days", {})
    total = len(days)
    completed = sum(1 for d in days.values() if d.get("morning") and d.get("evening"))
    await message.answer(f"📊 Выполнено полностью: {completed} из {total} дней")

@dp.message_handler(commands=["export"])
async def export_pdf(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    days = data.get(user_id, {}).get("days", {})

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Отчёт по 30-дневной анти-тревожной программе", ln=True, align="C")
    pdf.ln(10)

    for date, status in sorted(days.items()):
        morning = "✅" if status.get("morning") else "❌"
        evening = "✅" if status.get("evening") else "❌"
        pdf.cell(200, 10, txt=f"{date}: Утро {morning}, Вечер {evening}", ln=True)

    filename = f"report_{user_id}.pdf"
    pdf.output(filename)

    with open(filename, "rb") as file:
        await bot.send_document(chat_id=message.chat.id, document=file)

    os.remove(filename)

@dp.message_handler(commands=["panic"])
async def panic_tool(message: types.Message):
    anchors = [
        "🔸 Назови 3 предмета вокруг себя, которые ты видишь.",
        "🔹 Почувствуй 3 поверхности, которых ты касаешься.",
        "🔸 Сделай 3 медленных выдоха. Каждый дольше предыдущего.",
        "🔹 Скажи вслух: 'Я могу тревожиться и всё равно действовать.'",
        "🔸 Закрой глаза и прислушайся к 3 звукам вокруг."
    ]
    await message.answer(f"🛟 Якорь для заземления:\n{choice(anchors)}")


@dp.callback_query_handler(lambda c: c.data == "explain_today")
async def send_explanation(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, EXPLANATION_TEXT)

def schedule_daily_tasks():
    data = load_data()
    for user_id, user_data in data.items():
        offset = user_data.get("timezone_offset", 0)
        hour = (8 - offset) % 24
        scheduler.add_job(
            lambda uid=user_id: bot.send_message(uid, "⏰ Напоминание: напиши /today и начни день с маленького шага."),
            CronTrigger(hour=hour, minute=0),
            id=f"reminder_{user_id}",
            replace_existing=True
        )

async def on_startup(dp):
    schedule_daily_tasks()
    scheduler.start()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
