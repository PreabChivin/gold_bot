import requests

def get_prices():
    try:
        gold_url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=GC=F"
        silver_url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=SI=F"

        gold_res = requests.get(gold_url)
        silver_res = requests.get(silver_url)

        print("Gold status:", gold_res.status_code)
        print("Silver status:", silver_res.status_code)

        gold_data = gold_res.json()
        silver_data = silver_res.json()

        print("Gold data:", gold_data)
        print("Silver data:", silver_data)

        gold_price = gold_data["quoteResponse"]["result"][0]["regularMarketPrice"]
        silver_price = silver_data["quoteResponse"]["result"][0]["regularMarketPrice"]

        return {
            "gold": gold_price,
            "silver": silver_price
        }

    except Exception as e:
        print("❌ ERROR:", e)
        return None