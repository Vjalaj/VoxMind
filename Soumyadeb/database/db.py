# database/db.py

import sqlite3

DB_NAME = "assistant_memory.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            assistant_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_conversation(user_input, assistant_response):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO conversations (user_input, assistant_response)
        VALUES (?, ?)
    """, (user_input, assistant_response))

    conn.commit()
    conn.close()


def get_last_conversation():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_input, assistant_response
        FROM conversations
        ORDER BY id DESC
        LIMIT 1
    """)

    result = cursor.fetchone()
    conn.close()

    return result
