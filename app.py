from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os

# Store chat IDs that want scheduled updates
subscribed_chats = set()

async def start(update, context):
    subscribed_chats.add(update.effective_chat.id)
    await update.message.reply_text(
        "👋 Welcome to Gold & Silver Bot!\n\n"
        "Commands:\n"
        "/price - Get current prices\n"
        "/subscribe - Get auto updates every hour\n"
        "/unsubscribe - Stop auto updates"
    )

async def subscribe(update, context):
    subscribed_chats.add(update.effective_chat.id)
    await update.message.reply_text("✅ Subscribed! You'll get price updates every hour.")

async def unsubscribe(update, context):
    subscribed_chats.discard(update.effective_chat.id)
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

async def price(update, context):
    prices = get_prices()
    if not prices:
        await update.message.reply_text("❌ API Error")
        return
    await update.message.reply_text(
        f"🥇 Gold: ${prices['gold']:.2f}\n"
        f"🥈 Silver: ${prices['silver']:.4f}"
    )

async def post_init(app):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_scheduled_prices,
        trigger="interval",
        hours=1,
        args=[app]
    )
    scheduler.start()
    print("✅ Scheduler started")

def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).post_init(post_init).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()