# utils/assistant_utils.py

import re
from services.weather_api import get_weather
from config.settings import DEFAULT_CITY

def extract_city(command):
    # Try to extract city after "in"
    match = re.search(r"weather (?:in|of)\s+([a-zA-Z\s]+)", command)
    if match:
        return match.group(1).strip()

    # fallback
    return DEFAULT_CITY

def process_command(command):

    if "weather" in command:
        city = extract_city(command)
        return get_weather(city)

    return "Sorry, I did not understand that command."
