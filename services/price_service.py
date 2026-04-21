import requests

def get_prices():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        gold_url = "https://query1.finance.yahoo.com/v8/finance/quote?symbols=GC=F"
        silver_url = "https://query1.finance.yahoo.com/v8/finance/quote?symbols=SI=F"

        gold_res = requests.get(gold_url, headers=headers, timeout=10)
        silver_res = requests.get(silver_url, headers=headers, timeout=10)

        print("Gold status:", gold_res.status_code)
        print("Silver status:", silver_res.status_code)
        print("Gold raw:", gold_res.text[:500])   # <-- add this
        print("Silver raw:", silver_res.text[:500])  # <-- add this

        gold_data = gold_res.json()
        silver_data = silver_res.json()

        gold_result = gold_data.get("quoteResponse", {}).get("result", [])
        silver_result = silver_data.get("quoteResponse", {}).get("result", [])

        if not gold_result or not silver_result:
            print("❌ Empty result from Yahoo Finance")
            return None

        return {
            "gold": gold_result[0]["regularMarketPrice"],
            "silver": silver_result[0]["regularMarketPrice"]
        }

    except Exception as e:
        print("❌ ERROR:", e)
        return None