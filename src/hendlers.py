import os
import asyncio
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from geopy.geocoders import Nominatim
from geopy.adapters import AioHTTPAdapter
from dotenv import load_dotenv
from google import genai
from weather import get_weather 
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()
client= genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

user_language = {}

router = Router()

language_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en"),
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_ua")
        ]
    ]
)

@router.message(CommandStart())
async def start_command(message: types.Message):
    await message.answer(
        text="please select your language:",
        reply_markup=language_keyboard
    )

@router.callback_query(F.data == "lang_en")
async def process_lang_en(callback: types.CallbackQuery):
    user_language[callback.from_user.id] = "en"
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(
        text="📍 send my location",
        request_location=True
    ))
    await callback.message.answer(
        "Hi there! 👋 I'm your personal weather stylist.\n"
        "I'll help you pick the perfect outfit based on the weather in your city. To get started, please share your location!",
        reply_markup=builder.as_markup(resize_keyboard=True)
        )

@router.callback_query(F.data == "lang_ua")
async def process_lang_ua(callback: types.CallbackQuery):
    user_language[callback.from_user.id] = "ua"
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(
        text="📍 надіслати моє місцезнаходження",
        request_location=True
    ))
    await callback.message.answer(
        "Привіт! 👋 Я — твій особистий стиліст з погоди.\n"
        "Я допоможу тобі підібрати ідеальний наряд з урахуванням погоди у твоєму місті. Щоб почати, будь ласка, вкажи своє місцезнаходження!",
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

    city = None
    if location and location.raw.get("address"):
        address = location.raw["address"]
        city = address.get("city") or address.get("town") or address.get("village")

    if not city:
        await message.answer("Sorry, I couldn't determine your city from the provided location. Please try again.")
        return

    weather_data = await asyncio.to_thread(get_weather, city)
    if user_language.get(message.from_user.id) == "en":
        await message.answer(f"Your city is: {city}. Now, let's find the perfect outfit for you based on the weather in {city}!")
    elif user_language.get(message.from_user.id) == "ua":
        await message.answer(f"Ваше місто: {city}. Тепер знайдемо ідеальний наряд для вас з урахуванням погоди в {city}!")

    temperature, weather_description, humidity, wind_speed = weather_data

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-3.6-flash",
        contents=(
            f"Please suggest a stylish outfit suitable for the current weather in {city}; "
            f"first, take these parameters into account: {temperature}, "
            f"{weather_description}, {humidity}, and {wind_speed}. "
            f"And use this language for the answer: {user_language.get(message.from_user.id)} "
            "Just write a few sentences and use some emojis to make it more fun and engaging."
        )
    )

    await message.answer(response.text)
    
    print("KEY LOADED:", bool(os.getenv("GEMINI_API_KEY")))