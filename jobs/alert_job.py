from services.price_service import get_prices

last_price = None

async def check_price(context):
    global last_price

    data = get_prices()
    if not data:
        return

    if last_price:
        change = ((data["gold"] - last_price["gold"]) / last_price["gold"]) * 100

        if abs(change) >= 1:  # 1% threshold
            await context.bot.send_message(
                chat_id=context.job.chat_id,
                text=f"⚠️ Gold changed {round(change,2)}%\nNow: ${data['gold']}"
            )

    last_price = data