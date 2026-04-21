import requests
import time

def get_prices(retries=3, delay=2):
    headers = {"x-access-token": "goldapi-3wecn1mmo8bzn01-io"}

    for attempt in range(retries):
        try:
            gold_res = requests.get("https://www.goldapi.io/api/XAU/USD", headers=headers, timeout=10)
            silver_res = requests.get("https://www.goldapi.io/api/XAG/USD", headers=headers, timeout=10)

            print("Gold status:", gold_res.status_code)
            print("Gold raw:", gold_res.text)
            print("Silver status:", silver_res.status_code)
            print("Silver raw:", silver_res.text)

            gold_price = gold_res.json()["price"]
            silver_price = silver_res.json()["price"]

            return {"gold": gold_price, "silver": silver_price}

        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)

    print("❌ All retries failed")
    return None