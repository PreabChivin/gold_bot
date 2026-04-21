import os
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from services.price_service import get_prices

# ================== LOAD ENV ==================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set in .env")

# ================== LOGGING ==================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================== GLOBAL ==================
last_price = None


# ================== COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        "🤖 Gold & Silver Bot Ready!\n\n"
        "Commands:\n"
        "/price - Show current price\n"
        "🔔 Auto alert enabled (every 5 min)"
    )

    # Schedule alert job (every 5 minutes)
    context.job_queue.run_repeating(
        check_price,
        interval=300,
        first=10,
        chat_id=chat_id
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_prices()

    if not data:
        await update.message.reply_text("❌ Failed to fetch price from API")
        return

    await update.message.reply_text(
        f"💰 Gold: ${data['gold']} / oz\n"
        f"🥈 Silver: ${data['silver']} / oz"
    )


# ================== ALERT JOB ==================
async def check_price(context: ContextTypes.DEFAULT_TYPE):
    global last_price

    data = get_prices()
    if not data:
        return

    if last_price:
        change = ((data["gold"] - last_price["gold"]) / last_price["gold"]) * 100

        if abs(change) >= 1:  # 1% threshold
            await context.bot.send_message(
                chat_id=context.job.chat_id,
                text=(
                    f"⚠️ Gold price changed!\n"
                    f"📊 Change: {round(change, 2)}%\n"
                    f"💰 Now: ${data['gold']} / oz"
                )
            )

    last_price = data


# ================== MAIN ==================
if __name__ == "__main__":
    print("🚀 Starting Gold & Silver Bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))

    print("✅ Bot is running...")
    app.run_polling()