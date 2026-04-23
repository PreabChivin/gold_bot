import json
import logging
import os
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("gold_bot")

BASE_DIR = Path(__file__).resolve().parent
SUBS_FILE = BASE_DIR / "subscribed_chats.json"
HISTORY_FILE = BASE_DIR / "price_history.json"
ALERTS_FILE = BASE_DIR / "alerts.json"

API_BASE_URL = "https://www.goldapi.io/api"
REQUEST_TIMEOUT = 15
SUPPORTED_CHART_DAYS = {1: "24 Hours", 7: "7 Days", 30: "30 Days"}


def _read_json(path: Path, default):
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        LOGGER.warning("Could not read %s: %s", path.name, exc)
        return default


def _write_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def load_chats() -> set[int]:
    return {int(chat_id) for chat_id in _read_json(SUBS_FILE, [])}


def save_chats() -> None:
    _write_json(SUBS_FILE, sorted(subscribed_chats))


def load_history() -> list[dict]:
    return _read_json(HISTORY_FILE, [])


def save_history(history: list[dict]) -> None:
    _write_json(HISTORY_FILE, history)


def load_alerts() -> list[dict]:
    return _read_json(ALERTS_FILE, [])


def save_alerts(alerts: list[dict]) -> None:
    _write_json(ALERTS_FILE, alerts)


subscribed_chats = load_chats()


def get_bot_token() -> str | None:
    return os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")


def get_goldapi_key() -> str | None:
    return os.getenv("GOLDAPI_KEY") or os.getenv("GOLD_API_KEY")


def get_prices() -> tuple[dict | None, str | None]:
    api_key = get_goldapi_key()
    if not api_key:
        return None, (
            "Gold API key is missing. Set GOLDAPI_KEY in your environment or .env file."
        )

    headers = {
        "x-access-token": api_key,
        "Content-Type": "application/json",
    }

    try:
        gold_response = requests.get(
            f"{API_BASE_URL}/XAU/USD",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        silver_response = requests.get(
            f"{API_BASE_URL}/XAG/USD",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        LOGGER.exception("Price request failed")
        return None, f"Network error while contacting GoldAPI: {exc}"

    responses = {"gold": gold_response, "silver": silver_response}
    prices: dict[str, float] = {}

    for metal, response in responses.items():
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code != 200:
            message = payload.get("error") or payload.get("message") or response.text
            LOGGER.error(
                "GoldAPI returned %s for %s: %s",
                response.status_code,
                metal,
                message,
            )
            return None, (
                f"GoldAPI rejected the request for {metal} "
                f"({response.status_code}): {message}"
            )

        price = payload.get("price")
        if price is None:
            LOGGER.error("GoldAPI response missing price for %s: %s", metal, payload)
            return None, f"GoldAPI response for {metal} did not include a price."

        prices[metal] = float(price)

    return prices, None


def record_prices(prices: dict[str, float]) -> None:
    history = load_history()
    history.append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "gold": prices["gold"],
            "silver": prices["silver"],
        }
    )

    cutoff = datetime.utcnow() - timedelta(days=30)
    history = [
        item
        for item in history
        if datetime.fromisoformat(item["timestamp"]) > cutoff
    ]
    save_history(history)


def generate_chart(days: int):
    history = load_history()
    if not history:
        return None

    cutoff = datetime.utcnow() - timedelta(days=days)
    filtered = [
        item
        for item in history
        if datetime.fromisoformat(item["timestamp"]) > cutoff
    ]

    if len(filtered) < 2:
        return None

    timestamps = [datetime.fromisoformat(item["timestamp"]) for item in filtered]
    gold_prices = [item["gold"] for item in filtered]
    silver_prices = [item["silver"] for item in filtered]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
    fig.patch.set_facecolor("#151824")

    for axis in (ax1, ax2):
        axis.set_facecolor("#1d2233")
        axis.tick_params(colors="white")
        axis.xaxis.label.set_color("white")
        axis.yaxis.label.set_color("white")
        axis.title.set_color("white")
        axis.grid(True, color="#3a425a", linestyle="--", alpha=0.45)
        for spine in axis.spines.values():
            spine.set_edgecolor("#58617e")
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        axis.tick_params(axis="x", rotation=30)

    ax1.plot(timestamps, gold_prices, color="#f2c94c", linewidth=2)
    ax1.set_title("Gold (USD)")
    ax1.set_ylabel("Price")

    ax2.plot(timestamps, silver_prices, color="#d0d5dd", linewidth=2)
    ax2.set_title("Silver (USD)")
    ax2.set_ylabel("Price")

    plt.tight_layout(pad=2.0)
    buffer = BytesIO()
    plt.savefig(buffer, format="png", facecolor=fig.get_facecolor())
    buffer.seek(0)
    plt.close(fig)
    return buffer


async def check_alerts(app: Application, prices: dict[str, float]) -> None:
    alerts = load_alerts()
    remaining_alerts = []

    for alert in alerts:
        metal = alert["metal"]
        direction = alert["direction"]
        target = float(alert["target"])
        chat_id = int(alert["chat_id"])
        current = prices[metal]

        triggered = (direction == "above" and current >= target) or (
            direction == "below" and current <= target
        )

        if triggered:
            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "Price alert triggered!\n\n"
                        f"{metal.capitalize()} is now ${current:.2f}\n"
                        f"Target: {direction} ${target:.2f}"
                    ),
                )
            except Exception as exc:
                LOGGER.warning("Failed to send alert to %s: %s", chat_id, exc)
                remaining_alerts.append(alert)
        else:
            remaining_alerts.append(alert)

    save_alerts(remaining_alerts)


async def start(update, context) -> None:
    subscribed_chats.add(update.effective_chat.id)
    save_chats()
    await update.message.reply_text(
        "Welcome to Gold and Silver Bot.\n\n"
        "Commands:\n"
        "/price - Current prices\n"
        "/subscribe - Auto updates every 15 minutes\n"
        "/unsubscribe - Stop auto updates\n"
        "/chart 1 - Last 24 hours\n"
        "/chart 7 - Last 7 days\n"
        "/chart 30 - Last 30 days\n"
        "/setalert gold above 4800\n"
        "/setalert gold below 4700\n"
        "/setalert silver above 80\n"
        "/setalert silver below 70\n"
        "/listalerts - Show active alerts\n"
        "/cancelalert 1 - Cancel one alert\n"
        "/cancelalerts - Cancel all alerts"
    )


async def price(update, context) -> None:
    prices, error = get_prices()
    if error:
        await update.message.reply_text(f"Could not fetch prices.\n{error}")
        return

    await update.message.reply_text(
        f"Gold: ${prices['gold']:.2f}\n"
        f"Silver: ${prices['silver']:.4f}"
    )


async def subscribe(update, context) -> None:
    subscribed_chats.add(update.effective_chat.id)
    save_chats()
    await update.message.reply_text(
        "Subscribed. You will receive price updates every 15 minutes."
    )


async def unsubscribe(update, context) -> None:
    subscribed_chats.discard(update.effective_chat.id)
    save_chats()
    await update.message.reply_text("Unsubscribed from scheduled updates.")


async def chart(update, context) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/chart 1 - Last 24 hours\n"
            "/chart 7 - Last 7 days\n"
            "/chart 30 - Last 30 days"
        )
        return

    try:
        days = int(context.args[0])
        if days not in SUPPORTED_CHART_DAYS:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please use /chart 1, /chart 7, or /chart 30.")
        return

    await update.message.reply_text("Generating chart...")
    buffer = generate_chart(days)
    if not buffer:
        await update.message.reply_text(
            "Not enough data yet. The bot records prices every 15 minutes."
        )
        return

    await update.message.reply_photo(
        photo=buffer,
        caption=f"Gold and Silver - Last {SUPPORTED_CHART_DAYS[days]}",
    )


async def setalert(update, context) -> None:
    usage = (
        "Usage:\n"
        "/setalert gold above 4800\n"
        "/setalert gold below 4700\n"
        "/setalert silver above 80\n"
        "/setalert silver below 70"
    )

    if len(context.args) != 3:
        await update.message.reply_text(usage)
        return

    metal = context.args[0].lower()
    direction = context.args[1].lower()

    if metal not in {"gold", "silver"}:
        await update.message.reply_text("Metal must be 'gold' or 'silver'.")
        return

    if direction not in {"above", "below"}:
        await update.message.reply_text("Direction must be 'above' or 'below'.")
        return

    try:
        target = float(context.args[2])
    except ValueError:
        await update.message.reply_text("Price must be a number, for example 4800.")
        return

    alerts = load_alerts()
    alerts.append(
        {
            "chat_id": update.effective_chat.id,
            "metal": metal,
            "direction": direction,
            "target": target,
        }
    )
    save_alerts(alerts)

    await update.message.reply_text(
        "Alert saved.\n\n"
        f"{metal.capitalize()} {direction} ${target:.2f}"
    )


async def listalerts(update, context) -> None:
    alerts = load_alerts()
    user_alerts = [
        alert for alert in alerts if int(alert["chat_id"]) == update.effective_chat.id
    ]

    if not user_alerts:
        await update.message.reply_text(
            "You have no active alerts. Use /setalert to create one."
        )
        return

    lines = ["Your active alerts:"]
    for index, alert in enumerate(user_alerts, start=1):
        lines.append(
            f"{index}. {alert['metal'].capitalize()} "
            f"{alert['direction']} ${float(alert['target']):.2f}"
        )

    lines.append("")
    lines.append("Cancel one: /cancelalert 1")
    lines.append("Cancel all: /cancelalerts")
    await update.message.reply_text("\n".join(lines))


async def cancelalert(update, context) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: /cancelalert 1\nUse /listalerts to see alert numbers."
        )
        return

    try:
        index = int(context.args[0]) - 1
        if index < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please provide a valid alert number.")
        return

    alerts = load_alerts()
    user_alerts = [
        alert for alert in alerts if int(alert["chat_id"]) == update.effective_chat.id
    ]

    if index >= len(user_alerts):
        await update.message.reply_text(
            f"Alert #{index + 1} was not found. Use /listalerts to see your alerts."
        )
        return

    target_alert = user_alerts[index]
    alerts.remove(target_alert)
    save_alerts(alerts)

    await update.message.reply_text(
        "Alert cancelled.\n\n"
        f"{target_alert['metal'].capitalize()} "
        f"{target_alert['direction']} ${float(target_alert['target']):.2f}"
    )


async def cancelalerts(update, context) -> None:
    alerts = load_alerts()
    remaining = [
        alert for alert in alerts if int(alert["chat_id"]) != update.effective_chat.id
    ]
    save_alerts(remaining)
    await update.message.reply_text("All of your alerts have been cancelled.")


async def send_scheduled_prices(app: Application) -> None:
    prices, error = get_prices()
    if error:
        LOGGER.error("Scheduled update skipped: %s", error)
        return

    record_prices(prices)
    await check_alerts(app, prices)

    message = (
        "Scheduled update\n\n"
        f"Gold: ${prices['gold']:.2f}\n"
        f"Silver: ${prices['silver']:.4f}"
    )

    for chat_id in list(subscribed_chats):
        try:
            await app.bot.send_message(chat_id=chat_id, text=message)
        except Exception as exc:
            LOGGER.warning("Failed to send scheduled update to %s: %s", chat_id, exc)


async def post_init(app: Application) -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_scheduled_prices,
        trigger="interval",
        minutes=15,
        args=[app],
        max_instances=1,
    )
    scheduler.start()
    LOGGER.info("Scheduler started")


def main() -> None:
    token = get_bot_token()
    if not token:
        raise RuntimeError(
            "Telegram bot token is missing. Set BOT_TOKEN in your environment or .env file."
        )

    app = Application.builder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("chart", chart))
    app.add_handler(CommandHandler("setalert", setalert))
    app.add_handler(CommandHandler("listalerts", listalerts))
    app.add_handler(CommandHandler("cancelalert", cancelalert))
    app.add_handler(CommandHandler("cancelalerts", cancelalerts))

    LOGGER.info("Bot is running")
    app.run_polling()


if __name__ == "__main__":
    main()
