import sqlite3
from datetime import datetime

conn = sqlite3.connect("data/conversations.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    message TEXT,
    response TEXT,
    timestamp TEXT
)
""")
conn.commit()

def save_conversation(user, message, response):
    cur.execute(
        "INSERT INTO conversations VALUES (NULL,?,?,?,?)",
        (user, message, response, datetime.now().isoformat())
    )
    conn.commit()
