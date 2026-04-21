import sqlite3

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER,
    alert_threshold REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS prices (
    gold REAL,
    silver REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()