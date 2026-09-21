import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from hendlers import router

load_dotenv()

logging.basicConfig(level=logging.INFO)

token = os.getenv("TelegramBotToken")

bot = Bot(token)
dispatcher = Dispatcher()
dispatcher.include_router(router)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())