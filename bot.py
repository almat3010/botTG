import logging
import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.utils.markdown import hbold
from aiogram.client.default import DefaultBotProperties
from aiogram import Router
import cloudscraper
from bs4 import BeautifulSoup
import ssl
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Чтение API_TOKEN из переменной окружения
API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise ValueError("API_TOKEN не найден в переменных окружения")

CHECK_INTERVAL = 1800  # Проверка каждые 5 минут

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

subscribers: set[int] = set()
last_known_value = None

def fetch_countdown_text() -> str:
    url = "https://case-battle.at/case/awpasiimov"

    # Создаём кастомный SSL-контекст с отключённой проверкой
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    # Передаём контекст в cloudscraper
    scraper = cloudscraper.create_scraper(
        ssl_context=context,
        delay=10,
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )

    try:
        resp = scraper.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        elem = soup.select_one("#case-box-app > div.countdown > div:nth-child(3)")
        return elem.get_text(strip=True) if elem else "Элемент не найден"
    except Exception as e:
        return f"Ошибка при получении данных: {e}"

@router.message(Command("start"))
async def cmd_start(msg: Message):
    subscribers.add(msg.chat.id)
    await msg.answer("✅ Подписка на автоуведомления активна.\nНапиши /stop, чтобы отписаться.")

@router.message(Command("stop"))
async def cmd_stop(msg: Message):
    if msg.chat.id in subscribers:
        subscribers.discard(msg.chat.id)
        await msg.answer("❌ Подписка отключена.")
    else:
        await msg.answer("Ты и так не подписан 🙂")

@router.message(Command("check"))
async def cmd_check(msg: Message):
    result = fetch_countdown_text()
    await msg.answer(f"{hbold('Результат')}: {result}")

async def background_checker():
    global last_known_value
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        current_value = fetch_countdown_text()
        if current_value != last_known_value:
            last_known_value = current_value
            text = f"{hbold('Обновление!')} Новое значение: {current_value}"
            for chat_id in subscribers:
                try:
                    await bot.send_message(chat_id=chat_id, text=text)
                except Exception as e:
                    logging.warning(f"Не удалось отправить сообщение {chat_id}: {e}")

async def main():
    asyncio.create_task(background_checker())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
