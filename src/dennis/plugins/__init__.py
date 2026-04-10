# src/dennis/plugins/__init__.py

from . import python

PLUGINS = {
    "python": python,
}

def load_plugins():
    return []