import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

subscribers = set()
last_value = None  # для отслеживания изменений

async def get_countdown_text():
    try:
        options = uc.ChromeOptions()
        options.headless = True
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = uc.Chrome(options=options)
        driver.get("https://case-battle.at/case/awpasiimov")
        driver.implicitly_wait(15)

        element = driver.find_element(By.CSS_SELECTOR, "#case-box-app > div.countdown > div:nth-child(3)")
        text = element.text

        driver.quit()
        return text
    except Exception as e:
        return f"Ошибка при получении данных: {e}"

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("Привет! Используй /subscribe чтобы подписаться на уведомления.")

@dp.message(F.text == "/check")
async def cmd_check(message: Message):
    text = await asyncio.to_thread(get_countdown_text)
    await message.answer(f"Результат: {text}")

@dp.message(F.text == "/subscribe")
async def cmd_subscribe(message: Message):
    user_id = message.chat.id
    subscribers.add(user_id)
    await message.answer("✅ Подписка оформлена. Буду слать уведомления при изменениях!")

@dp.message(F.text == "/unsubscribe")
async def cmd_unsubscribe(message: Message):
    user_id = message.chat.id
    subscribers.discard(user_id)
    await message.answer("❌ Подписка отменена.")

@dp.message(F.text == "/stop")
async def cmd_stop(message: Message):
    await message.answer("Бот остановлен.")
    await bot.session.close()
    exit(0)

async def auto_check_loop():
    global last_value
    while True:
        await asyncio.sleep(1800)  # проверка раз в 1800 секунд
        text = await asyncio.to_thread(get_countdown_text)

        if "Ошибка" not in text and text != last_value:
            last_value = text
            for user_id in subscribers:
                try:
                    await bot.send_message(user_id, f"🔔 Обновление: {text}")
                except Exception as e:
                    logging.warning(f"Не удалось отправить сообщение {user_id}: {e}")

async def main():
    asyncio.create_task(auto_check_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
