import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from hendlers import router

load_dotenv()

token = os.getenv("TelegramBotToken")

bot = Bot(token)
dispatcher = Dispatcher()
dispatcher.include_router(router)

async def main():
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())