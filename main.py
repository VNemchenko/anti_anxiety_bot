import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from random import choice

API_TOKEN = os.getenv("BOT_TOKEN")  # Установи переменную окружения

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "users_data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

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
        data[user_id] = {"days": {}, "start_date": get_today()}
        save_data(data)
    await message.answer("👋 Добро пожаловать в 30-дневную анти-тревожную программу! Каждый день я буду давать тебе задания. Напиши /today чтобы начать.")

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

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
