# jobs/scheduler.py

import time
from services.price_service import get_prices

last_price = None

def run_scheduler(bot):
    global last_price

    while True:
        data = get_prices()

        if last_price:
            change = abs(data["gold"] - last_price["gold"])

            if change > 1:  # threshold
                bot.send_message(chat_id=YOUR_CHAT_ID,
                                 text=f"⚠️ Gold changed: {data['gold']}")

        last_price = data
        time.sleep(300)  # every 5 min