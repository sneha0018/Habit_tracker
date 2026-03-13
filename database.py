import sqlite3
from flask import g
import os

DATABASE = 'habits.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS habits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            icon        TEXT    DEFAULT '⭐',
            color       TEXT    DEFAULT '#a78bfa',
            goal        INTEGER DEFAULT 30,
            frequency   TEXT    DEFAULT 'daily',
            created_at  TEXT    DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id    INTEGER NOT NULL,
            date        TEXT    NOT NULL,
            UNIQUE(habit_id, date)
        );
    ''')
    db.commit()
    db.close()