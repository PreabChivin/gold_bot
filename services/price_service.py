# services/price_service.py

import requests
import os

API_KEY = os.getenv("API_KEY")

def get_prices():
    url = f"https://metals-api.com/api/latest?access_key={API_KEY}&base=USD&symbols=XAU,XAG"
    data = requests.get(url).json()

    return {
        "gold": data["rates"]["XAU"],
        "silver": data["rates"]["XAG"]
    }