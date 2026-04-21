import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set!")

# Dummy price function
def get_prices():
    return {
        "gold": "$2300 / oz",
        "silver": "$27 / oz"
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Gold & Silver Bot Ready!\nUse /price"
    )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_prices()
    await update.message.reply_text(
        f"💰 Gold: {data['gold']}\n🥈 Silver: {data['silver']}"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))

    print("🚀 Bot running...")
    app.run_polling()