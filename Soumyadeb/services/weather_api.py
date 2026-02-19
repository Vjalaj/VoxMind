# services/weather_api.py

import requests
from config.settings import API_KEY

def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    try:
        response = requests.get(url)
        data = response.json()

        if data["cod"] == 200:
            temp = data["main"]["temp"]
            description = data["weather"][0]["description"]

            return f"The current temperature in {city} is {temp} degree Celsius with {description}."

        else:
            return "Sorry, I could not fetch the weather."

    except Exception as e:
        return "Weather service is currently unavailable."
