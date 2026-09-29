import os
import sys

base = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(base, "src"), os.path.join(base, "..", "src")):
    if os.path.isdir(p):
        sys.path.insert(0, p)

from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from hendlers import router

dp = Dispatcher()
dp.include_router(router)

app = FastAPI()


@app.post("/{path:path}")
async def webhook(request: Request, path: str = ""):
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