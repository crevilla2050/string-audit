import mysql.connector

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "dennis",
    "password": "dennis",
    "database": "dennis_core",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)