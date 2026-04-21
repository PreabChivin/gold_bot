# services/price_service.py

import requests

def get_prices():
    try:
        gold_url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=GC=F"
        silver_url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=SI=F"

        gold_data = requests.get(gold_url).json()
        silver_data = requests.get(silver_url).json()

        gold_price = gold_data["quoteResponse"]["result"][0]["regularMarketPrice"]
        silver_price = silver_data["quoteResponse"]["result"][0]["regularMarketPrice"]

        return {
            "gold": gold_price,
            "silver": silver_price
        }

    except Exception as e:
        print("ERROR:", e)
        return None