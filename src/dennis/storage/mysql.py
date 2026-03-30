# storage/mysql.py

import pymysql
from .base import DennisStorage
from .query import normalize_sql


class MySQLStorage(DennisStorage):
    flavor = "mysql"

    def __init__(self, host, user, password, db, port=3306):
        self.conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=db,
            port=port,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
        self._cursor = None

    def execute(self, sql, params=None):
        sql = normalize_sql(sql, self.flavor)
        self._cursor = self.conn.cursor()
        self._cursor.execute(sql, params or [])
        return self._cursor

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def begin(self):
        self.conn.begin()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()