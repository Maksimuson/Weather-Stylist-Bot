import os
import asyncio
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from geopy.geocoders import Nominatim
from geopy.adapters import AioHTTPAdapter
from dotenv import load_dotenv
from google import genai


load_dotenv()
client= genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

router = Router()

@router.message(CommandStart())
async def start_command(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(
        text="📍 send my location",
        request_location=True
    ))
    await message.answer(
        "Hi there! 👋 I'm your personal weather stylist.\n"
        "I'll help you pick the perfect outfit based on the weather in your city. To get started, please share your location!",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@router.message(F.location)
async def location_handler(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude

    async with Nominatim(
        user_agent="weather_stylist_for_you_bot",
        adapter_factory=AioHTTPAdapter
    ) as geolocator:
        location = await geolocator.reverse((lat, lon))

        if location and location.raw.get("address"):
            address = location.raw["address"]
            city = address.get("city") or address.get("town") or address.get("village")
        else:
            await message.answer("Sorry, I couldn't determine your city from the provided location. Please try again.")
            return

    await message.answer(f"Your city is: {city}. Now, let's find the perfect outfit for you based on the weather in {city}!")

    response = await asyncio.to_thread(
    client.models.generate_content,
    model="gemini-3.6-flash",
    contents=f"Please provide a stylish outfit recommendation for the current weather in {city}"

    )

    await message.answer(response.text)
    
    print("KEY LOADED:", bool(os.getenv("GEMINI_API_KEY")))
