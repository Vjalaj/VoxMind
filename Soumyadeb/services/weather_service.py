import requests
import time

CACHE = {}
CACHE_TTL = 600

class WeatherService:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_weather(self, city):
        now = time.time()

        if city in CACHE and now - CACHE[city]["time"] < CACHE_TTL:
            return CACHE[city]["data"]

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }

        response = requests.get(url, params=params).json()
        CACHE[city] = {"data": response, "time": now}
        return response
