
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from services.price_service import get_prices
import os
from dotenv import load_dotenv, find_dotenv

# Improved loading - this finds and loads .env more reliably
dotenv_path = find_dotenv()
print(f"Found .env at: {dotenv_path}")

if dotenv_path:
    load_dotenv(dotenv_path, override=True)   # override=True forces reload
    print("✅ .env file loaded successfully")
else:
    print("❌ .env file NOT found by dotenv")

print("=== DEBUG: Environment Variables ===")
print(f"Current working directory: {os.getcwd()}")
print(f"BOT_TOKEN = {os.getenv('BOT_TOKEN')}")
print("===================================")

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set! Please check your .env file content and format.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Gold & Silver Bot Ready! \nUse /price to check current prices.")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = get_prices()
        await update.message.reply_text(
            f"💰 Gold: {data.get('gold', 'N/A')}\n"
            f"🥈 Silver: {data.get('silver', 'N/A')}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching prices: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Gold & Silver Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))

    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()