"""Phases 4, 10, 12: SQLite connection + tables.
Tables: documents, chats, messages, memories (see IMPLEMENTATION_GUIDE.md)."""
import sqlite3
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # TODO: CREATE TABLE IF NOT EXISTS documents/chats/messages/memories
    pass
