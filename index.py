import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from hendlers import router

dp = Dispatcher()
dp.include_router(router)

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    secret = os.getenv("TELEGRAM_SECRET")
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        raise HTTPException(status_code=403)

    bot = Bot(os.environ["TelegramBotToken"])
    try:
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await dp.feed_update(bot, update)
    finally:
        await bot.session.close()
    return {"ok": True}