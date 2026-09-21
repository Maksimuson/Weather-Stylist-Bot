import os
import asyncio
import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from geopy.geocoders import Nominatim
from geopy.adapters import AioHTTPAdapter
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
from weather import get_weather
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# gemini-3.1-flash-lite: currently stable, fast and cheap (no announced
# retirement date). "gemini-3.6-flash" from the old code doesn't exist,
# which is why every request was failing with 503.
MODEL_NAME = "gemini-3.1-flash-lite"

logger = logging.getLogger(__name__)

router = Router()

# Per-user state: {user_id: {"lang": "en"/"ua", "sex": "male"/"female"}}
user_data: dict[int, dict] = {}

language_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en"),
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_ua"),
        ]
    ]
)

sex_keyboard_en = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="♂ Male", callback_data="sex_male"),
            InlineKeyboardButton(text="♀ Female", callback_data="sex_female"),
        ]
    ]
)

sex_keyboard_ua = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="♂ Чоловік", callback_data="sex_male"),
            InlineKeyboardButton(text="♀ Жінка", callback_data="sex_female"),
        ]
    ]
)


@router.message(CommandStart())
async def start_command(message: types.Message):
    user_data[message.from_user.id] = {}
    await message.answer(
        text="Please select your language / Оберіть мову:",
        reply_markup=language_keyboard,
    )


@router.callback_query(F.data.in_({"lang_en", "lang_ua"}))
async def process_language(callback: types.CallbackQuery):
    lang = "en" if callback.data == "lang_en" else "ua"
    user_data.setdefault(callback.from_user.id, {})["lang"] = lang

    if lang == "en":
        await callback.message.answer("Please select your gender:", reply_markup=sex_keyboard_en)
    else:
        await callback.message.answer("Будь ласка, оберіть вашу стать:", reply_markup=sex_keyboard_ua)

    await callback.answer()


@router.callback_query(F.data.in_({"sex_male", "sex_female"}))
async def process_sex(callback: types.CallbackQuery):
    sex = "male" if callback.data == "sex_male" else "female"
    data = user_data.setdefault(callback.from_user.id, {})
    data["sex"] = sex
    lang = data.get("lang", "en")

    builder = ReplyKeyboardBuilder()
    if lang == "en":
        builder.add(types.KeyboardButton(text="📍 Send my location", request_location=True))
        await callback.message.answer(
            "Hi there! 👋 I'm your personal weather stylist.\n"
            "I'll help you pick the perfect outfit based on the weather in your city. "
            "To get started, please share your location!",
            reply_markup=builder.as_markup(resize_keyboard=True),
        )
    else:
        builder.add(types.KeyboardButton(text="📍 Надіслати моє місцезнаходження", request_location=True))
        await callback.message.answer(
            "Привіт! 👋 Я — твій особистий стиліст з погоди.\n"
            "Я допоможу тобі підібрати ідеальний наряд з урахуванням погоди у твоєму місті. "
            "Щоб почати, будь ласка, вкажи своє місцезнаходження!",
            reply_markup=builder.as_markup(resize_keyboard=True),
        )

    await callback.answer()


@router.message(F.location)
async def location_handler(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    lang = user_data.get(message.from_user.id, {}).get("lang", "en")

    try:
        async with Nominatim(
            user_agent="weather_stylist_for_you_bot",
            adapter_factory=AioHTTPAdapter,
        ) as geolocator:
            location = await geolocator.reverse((lat, lon))
    except Exception:
        logger.exception("Geocoding failed")
        location = None

    city = None
    if location and location.raw.get("address"):
        address = location.raw["address"]
        city = address.get("city") or address.get("town") or address.get("village")

    if not city:
        text = (
            "Sorry, I couldn't determine your city from the provided location. Please try again."
            if lang == "en"
            else "Вибачте, не вдалося визначити ваше місто. Спробуйте ще раз."
        )
        await message.answer(text)
        return

    weather_data = await asyncio.to_thread(get_weather, city)
    if not weather_data:
        text = (
            f"Sorry, I couldn't fetch the weather for {city}. Please try again later."
            if lang == "en"
            else f"Вибачте, не вдалося отримати погоду для {city}. Спробуйте пізніше."
        )
        await message.answer(text)
        return

    if lang == "en":
        await message.answer(f"Your city is: {city}. Let's find the perfect outfit for you!")
    else:
        await message.answer(f"Ваше місто: {city}. Тепер знайдемо ідеальний наряд для вас!")

    temperature, weather_description, humidity, wind_speed = weather_data
    sex = user_data.get(message.from_user.id, {}).get("sex", "unisex")

    prompt = (
        f"Suggest one stylish {sex} outfit suitable for the current weather in {city}. "
        f"Weather data: temperature {temperature}°C, {weather_description}, "
        f"humidity {humidity}%, wind speed {wind_speed} m/s. "
        f"Reply in this language: {lang}. "
        "Keep it to 2-3 short sentences and add a couple of fitting emojis."
    )

    try:
        # Native async call (client.aio) instead of asyncio.to_thread —
        # avoids spinning up a worker thread just to wait on network I/O.
        # AFC is explicitly disabled since no tools/functions are used;
        # this also silences the noisy AFC warning from the SDK.
        response = await client.aio.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                max_output_tokens=200,
                automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        await message.answer(response.text)
    except Exception:
        logger.exception("Gemini request failed")
        text = (
            "Sorry, the styling assistant is temporarily unavailable. Please try again in a moment."
            if lang == "en"
            else "Вибачте, стиліст тимчасово недоступний. Спробуйте трохи пізніше."
        )
        await message.answer(text)