# Gold Bot

Telegram bot for gold and silver price updates, charts, and alerts.

## Environment variables

Create or update `.env` with:

```env
BOT_TOKEN=your_telegram_bot_token
GOLDAPI_KEY=your_goldapi_key
```

The app also accepts `TELEGRAM_BOT_TOKEN` and `GOLD_API_KEY`, but `BOT_TOKEN` and `GOLDAPI_KEY` are the default names used by the project.

## Run

```powershell
pip install -r requirements.txt
python app.py
```
