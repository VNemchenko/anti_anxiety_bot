import json
import os
from datetime import datetime, time
from aiogram import Bot, Dispatcher, executor, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from random import choice
from fpdf import FPDF

API_TOKEN = os.getenv("BOT_TOKEN")  # Установи переменную окружения

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

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

@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"days": {}, "start_date": get_today(), "timezone_offset": 0}
        save_data(data)
    await message.answer("👋 Добро пожаловать в 30-дневную анти-тревожную программу! Каждый день я буду давать тебе задания. Напиши /today чтобы начать.\n\nЕсли хочешь, чтобы напоминания приходили в определённое время — используй команду /set_timezone +N или -N (например, /set_timezone +3 для Москвы).")

@dp.message_handler(commands=["set_timezone"])
async def set_timezone(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("⚠️ Использование: /set_timezone +3 или /set_timezone -5")
        return
    try:
        offset = int(parts[1])
    except ValueError:
        await message.answer("⚠️ Неверный формат. Пример: /set_timezone +2")
        return
    data.setdefault(user_id, {"days": {}, "start_date": get_today()})
    data[user_id]["timezone_offset"] = offset
    save_data(data)
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

    await message.answer(
        f"📅 День: {today}\n\n🧘 Утро:\n1. Подыши: вдох 4с — пауза 4с — выдох 6с.\n2. Задай вопрос: что я могу сделать сегодня несмотря на тревогу?\n3. Маленький шаг — неважно какой, но сделай.\n\n🌙 Вечер:\n1. Выгрузи в заметку все мысли.\n2. Определи, что требует действия, а что просто шум.\n3. Поблагодари себя.\n\nНапиши /done_morning или /done_evening по мере выполнения."
    )

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

if __name__ == '__main__':
    schedule_daily_tasks()
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)
