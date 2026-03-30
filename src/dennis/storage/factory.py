# storage/factory.py

from .sqlite import SQLiteStorage
from .mysql import MySQLStorage


def create_storage(config: dict):
    engine = config.get("engine")

    if engine == "sqlite":
        return SQLiteStorage(config["path"])

    if engine == "mysql":
        return MySQLStorage(
            host=config["host"],
            user=config["user"],
            password=config["password"],
            db=config["database"],
            port=config.get("port", 3306),
        )

    raise ValueError(f"Unknown storage engine: {engine}")