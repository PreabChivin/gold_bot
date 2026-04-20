import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from services.price_service import get_prices

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Gold & Silver Bot Ready!")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_prices()
    await update.message.reply_text(
        f"💰 Gold: {data['gold']}\n🥈 Silver: {data['silver']}"
    )

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("price", price))

app.run_polling()