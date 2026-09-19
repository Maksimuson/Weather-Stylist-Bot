import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_weather(city):
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={os.getenv("WeatherAPIKey")}&units=metric&lang=ru'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        temperature = data['main']['temp']
        weather_description = data['weather'][0]['description']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']

        print(f"Temperature: {temperature}°C")
        print(f"Weather: {weather_description}")
        print(f"Humidity: {humidity}%")
        print(f"Wind Speed: {wind_speed} m/s")

        return temperature, weather_description, humidity, wind_speed
    else:
        print("Error occurred while fetching weather data.")
        return None