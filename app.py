import os
import json
import requests
import time
from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ── Persistent subscriptions ──────────────────────────────
SUBS_FILE = "subscribed_chats.json"

def load_chats():
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_chats():
    with open(SUBS_FILE, "w") as f:
        json.dump(list(subscribed_chats), f)

subscribed_chats = load_chats()

# ── API ───────────────────────────────────────────────────
def get_prices(retries=3, delay=2):
    headers = {"x-access-token": os.getenv("GOLDAPI_KEY")}
    for attempt in range(retries):
        try:
            gold_res = requests.get("https://www.goldapi.io/api/XAU/USD", headers=headers, timeout=10)
            silver_res = requests.get("https://www.goldapi.io/api/XAG/USD", headers=headers, timeout=10)
            gold_price = gold_res.json()["price"]
            silver_price = silver_res.json()["price"]
            return {"gold": gold_price, "silver": silver_price}
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    print("❌ All retries failed")
    return None

# ── Handlers ──────────────────────────────────────────────
async def start(update, context):
    subscribed_chats.add(update.effective_chat.id)
    save_chats()
    await update.message.reply_text(
        "👋 Welcome to Gold & Silver Bot!\n\n"
        "Commands:\n"
        "/price - Get current prices\n"
        "/subscribe - Get auto updates every 15 minutes\n"
        "/unsubscribe - Stop auto updates"
    )

async def price(update, context):
    prices = get_prices()
    if not prices:
        await update.message.reply_text("❌ API Error")
        return
    await update.message.reply_text(
        f"🥇 Gold: ${prices['gold']:.2f}\n"
        f"🥈 Silver: ${prices['silver']:.4f}"
    )

async def subscribe(update, context):
    subscribed_chats.add(update.effective_chat.id)
    save_chats()
    await update.message.reply_text("✅ Subscribed! You'll get price updates every 15 minutes.")

async def unsubscribe(update, context):
    subscribed_chats.discard(update.effective_chat.id)
    save_chats()
    await update.message.reply_text("❌ Unsubscribed from auto updates.")

async def send_scheduled_prices(app):
    prices = get_prices()
    if not prices:
        return
    message = (
        f"🕐 Scheduled Update\n\n"
        f"🥇 Gold: ${prices['gold']:.2f}\n"
        f"🥈 Silver: ${prices['silver']:.4f}"
    )
    for chat_id in subscribed_chats:
        try:
            await app.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            print(f"⚠️ Failed to send to {chat_id}: {e}")

# ── Scheduler ─────────────────────────────────────────────
async def post_init(app):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_scheduled_prices,
        trigger="interval",
        minutes=15,
        args=[app]
    )
    scheduler.start()
    print("✅ Scheduler started")

# ── Main ──────────────────────────────────────────────────
def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()