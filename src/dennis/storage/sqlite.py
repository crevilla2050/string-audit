# storage/sqlite.py

import sqlite3
from .base import DennisStorage
from .query import normalize_sql


class SQLiteStorage(DennisStorage):
    flavor = "sqlite"

    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._cursor = None

    def execute(self, sql, params=None):
        sql = normalize_sql(sql, self.flavor)
        self._cursor = self.conn.cursor()
        self._cursor.execute(sql, params or [])
        return self._cursor

    def fetchone(self):
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

    def begin(self):
        self.conn.execute("BEGIN")

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()