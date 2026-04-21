import os
import json
import requests
import time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from io import BytesIO
from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ── Persistent data ───────────────────────────────────────
SUBS_FILE = "subscribed_chats.json"
HISTORY_FILE = "price_history.json"
ALERTS_FILE = "alerts.json"

def load_chats():
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_chats():
    with open(SUBS_FILE, "w") as f:
        json.dump(list(subscribed_chats), f)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def load_alerts():
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_alerts(alerts):
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f)

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

def record_prices():
    prices = get_prices()
    if not prices:
        return
    history = load_history()
    history.append({
        "timestamp": datetime.utcnow().isoformat(),
        "gold": prices["gold"],
        "silver": prices["silver"]
    })
    cutoff = datetime.utcnow() - timedelta(days=30)
    history = [h for h in history if datetime.fromisoformat(h["timestamp"]) > cutoff]
    save_history(history)

# ── Chart ─────────────────────────────────────────────────
def generate_chart(days):
    history = load_history()
    if not history:
        return None

    cutoff = datetime.utcnow() - timedelta(days=days)
    filtered = [h for h in history if datetime.fromisoformat(h["timestamp"]) > cutoff]

    if len(filtered) < 2:
        return None

    timestamps = [datetime.fromisoformat(h["timestamp"]) for h in filtered]
    gold_prices = [h["gold"] for h in filtered]
    silver_prices = [h["silver"] for h in filtered]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
    fig.patch.set_facecolor("#1a1a2e")

    for ax in [ax1, ax2]:
        ax.set_facecolor("#16213e")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")

    ax1.plot(timestamps, gold_prices, color="#FFD700", linewidth=2)
    ax1.set_title("🥇 Gold (USD)")
    ax1.set_ylabel("Price (USD)")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax1.tick_params(axis="x", rotation=30)
    ax1.grid(True, color="#333", linestyle="--", alpha=0.5)

    ax2.plot(timestamps, silver_prices, color="#C0C0C0", linewidth=2)
    ax2.set_title("🥈 Silver (USD)")
    ax2.set_ylabel("Price (USD)")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax2.tick_params(axis="x", rotation=30)
    ax2.grid(True, color="#333", linestyle="--", alpha=0.5)

    plt.tight_layout(pad=2.0)
    buf = BytesIO()
    plt.savefig(buf, format="png", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close()
    return buf

# ── Alert checker ─────────────────────────────────────────
async def check_alerts(app):
    prices = get_prices()
    if not prices:
        return

    alerts = load_alerts()
    remaining = []

    for alert in alerts:
        metal = alert["metal"]
        direction = alert["direction"]
        target = alert["target"]
        chat_id = alert["chat_id"]
        current = prices[metal]

        triggered = (direction == "above" and current >= target) or \
                    (direction == "below" and current <= target)

        if triggered:
            emoji = "🥇" if metal == "gold" else "🥈"
            arrow = "📈" if direction == "above" else "📉"
            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🚨 Price Alert Triggered!\n\n"
                        f"{emoji} {metal.capitalize()} is now ${current:.2f}\n"
                        f"{arrow} Your target: {direction} ${target:.2f}"
                    )
                )
            except Exception as e:
                print(f"⚠️ Failed to send alert to {chat_id}: {e}")
        else:
            remaining.append(alert)

    save_alerts(remaining)

# ── Handlers ──────────────────────────────────────────────
async def start(update, context):
    subscribed_chats.add(update.effective_chat.id)
    save_chats()
    await update.message.reply_text(
        "👋 Welcome to Gold & Silver Bot!\n\n"
        "Commands:\n"
        "/price - Get current prices\n"
        "/subscribe - Get auto updates every 15 minutes\n"
        "/unsubscribe - Stop auto updates\n"
        "/chart 1 - Chart for last 24 hours\n"
        "/chart 7 - Chart for last 7 days\n"
        "/chart 30 - Chart for last 30 days\n"
        "/setalert gold above 4800 - Alert when gold > $4800\n"
        "/setalert gold below 4700 - Alert when gold < $4700\n"
        "/setalert silver above 80 - Alert when silver > $80\n"
        "/setalert silver below 70 - Alert when silver < $70\n"
        "/listalerts - View your active alerts\n"
        "/cancelalert 1 - Cancel alert number 1\n"
        "/cancelalerts - Cancel all your alerts"
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

async def chart(update, context):
    if not context.args:
        await update.message.reply_text(
            "📊 Usage:\n"
            "/chart 1 - Last 24 hours\n"
            "/chart 7 - Last 7 days\n"
            "/chart 30 - Last 30 days"
        )
        return
    try:
        days = int(context.args[0])
        if days not in [1, 7, 30]:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Please use /chart 1, /chart 7, or /chart 30")
        return

    await update.message.reply_text("📊 Generating chart...")
    buf = generate_chart(days)
    if not buf:
        await update.message.reply_text(
            "⚠️ Not enough data yet. The bot collects prices every 15 minutes. "
            "Please try again later."
        )
        return

    period = {1: "24 Hours", 7: "7 Days", 30: "30 Days"}[days]
    await update.message.reply_photo(
        photo=buf,
        caption=f"📈 Gold & Silver — Last {period}"
    )

async def setalert(update, context):
    usage = (
        "📋 Usage:\n"
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

    if metal not in ["gold", "silver"]:
        await update.message.reply_text("❌ Metal must be 'gold' or 'silver'")
        return
    if direction not in ["above", "below"]:
        await update.message.reply_text("❌ Direction must be 'above' or 'below'")
        return
    try:
        target = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Price must be a number e.g. 4800")
        return

    alerts = load_alerts()
    alerts.append({
        "chat_id": update.effective_chat.id,
        "metal": metal,
        "direction": direction,
        "target": target
    })
    save_alerts(alerts)

    emoji = "🥇" if metal == "gold" else "🥈"
    arrow = "📈" if direction == "above" else "📉"
    await update.message.reply_text(
        f"✅ Alert set!\n\n"
        f"{emoji} {metal.capitalize()} {arrow} {direction} ${target:.2f}\n\n"
        f"You'll be notified when the price hits your target."
    )

async def listalerts(update, context):
    alerts = load_alerts()
    user_alerts = [a for a in alerts if a["chat_id"] == update.effective_chat.id]

    if not user_alerts:
        await update.message.reply_text("📋 You have no active alerts.\nUse /setalert to create one.")
        return

    lines = ["📋 Your active alerts:\n"]
    for i, a in enumerate(user_alerts, 1):
        emoji = "🥇" if a["metal"] == "gold" else "🥈"
        arrow = "📈" if a["direction"] == "above" else "📉"
        lines.append(f"{i}. {emoji} {a['metal'].capitalize()} {arrow} {a['direction']} ${a['target']:.2f}")

    lines.append("\n💡 Cancel one: /cancelalert 1")
    lines.append("💡 Cancel all: /cancelalerts")
    await update.message.reply_text("\n".join(lines))

async def cancelalert(update, context):
    if not context.args:
        await update.message.reply_text("❌ Usage: /cancelalert 1\nUse /listalerts to see alert numbers.")
        return

    try:
        index = int(context.args[0]) - 1
        if index < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid alert number e.g. /cancelalert 1")
        return

    alerts = load_alerts()
    user_alerts = [a for a in alerts if a["chat_id"] == update.effective_chat.id]

    if index >= len(user_alerts):
        await update.message.reply_text(f"❌ Alert #{index + 1} not found. Use /listalerts to see your alerts.")
        return

    target_alert = user_alerts[index]
    alerts.remove(target_alert)
    save_alerts(alerts)

    emoji = "🥇" if target_alert["metal"] == "gold" else "🥈"
    arrow = "📈" if target_alert["direction"] == "above" else "📉"
    await update.message.reply_text(
        f"🗑 Alert cancelled:\n\n"
        f"{emoji} {target_alert['metal'].capitalize()} {arrow} {target_alert['direction']} ${target_alert['target']:.2f}"
    )

async def cancelalerts(update, context):
    alerts = load_alerts()
    remaining = [a for a in alerts if a["chat_id"] != update.effective_chat.id]
    save_alerts(remaining)
    await update.message.reply_text("🗑 All your alerts have been cancelled.")

# ── Scheduled job ─────────────────────────────────────────
async def send_scheduled_prices(app):
    record_prices()
    await check_alerts(app)
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
    app.add_handler(CommandHandler("chart", chart))
    app.add_handler(CommandHandler("setalert", setalert))
    app.add_handler(CommandHandler("listalerts", listalerts))
    app.add_handler(CommandHandler("cancelalert", cancelalert))
    app.add_handler(CommandHandler("cancelalerts", cancelalerts))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()