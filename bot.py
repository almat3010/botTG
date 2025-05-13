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
import urllib3
from playwright.async_api import async_playwright


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

async def fetch_countdown_text() -> str:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto("https://case-battle.at/case/awpasiimov", timeout=20000)
            
            # Ждём полной загрузки JS + XHR
            await page.wait_for_load_state("networkidle", timeout=20000)

            # Ждём появления нужного элемента
            try:
                await page.wait_for_selector("#case-box-app > div.countdown > div:nth-child(3)", timeout=20000)
                text = await page.inner_text("#case-box-app > div.countdown > div:nth-child(3)")
            except Exception:
                text = "❌ Элемент не найден или загрузка не завершилась."

            await browser.close()
            return text
    except Exception as e:
        return f"🚨 Ошибка при получении данных: {e}"

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
    result = await fetch_countdown_text()
    await msg.answer(f"{hbold('Результат')}: {result}")

async def background_checker():
    global last_known_value
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        current_value = await fetch_countdown_text()
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
