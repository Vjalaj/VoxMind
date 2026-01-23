import sqlite3

conn = sqlite3.connect("data/users.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    preferences TEXT
)
""")
conn.commit()

def save_user(username, preferences):
    cur.execute(
        "INSERT OR REPLACE INTO users VALUES (?,?)",
        (username, preferences)
    )
    conn.commit()
