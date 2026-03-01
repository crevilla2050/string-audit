# storage/base.py

from abc import ABC, abstractmethod


class DennisStorage(ABC):
    flavor: str  # "sqlite" or "mysql"

    @abstractmethod
    def execute(self, sql: str, params=None):
        pass

    @abstractmethod
    def fetchone(self):
        pass

    @abstractmethod
    def fetchall(self):
        pass

    @abstractmethod
    def begin(self):
        pass

    @abstractmethod
    def commit(self):
        pass

    @abstractmethod
    def rollback(self):
        pass

    @abstractmethod
    def close(self):
        pass