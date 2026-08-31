# src/dennis/plugins/__init__.py

from pathlib import Path
import importlib.util


PLUGIN_DIR = Path.home() / ".dennis" / "plugins"


def _load_plugin_file(path):
    """Load and validate a single external Dennis plugin."""

    spec = importlib.util.spec_from_file_location(
        f"dennis_user_plugin_{path.stem}",
        path,
    )

    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception:
        return None

    # Required plugin interface.
    if not hasattr(module, "PLUGIN_NAME"):
        return None

    if not hasattr(module, "SUPPORTED_EXTENSIONS"):
        return None

    if not hasattr(module, "scan_file"):
        return None

    return module


def load_plugins():
    """Discover and load installed Dennis scanner plugins."""

    plugins = []

    if not PLUGIN_DIR.exists():
        return plugins

    for path in sorted(PLUGIN_DIR.glob("*.py")):

        # Ignore private/helper files.
        if path.name.startswith("_"):
            continue

        plugin = _load_plugin_file(path)

        if plugin is None:
            continue

        plugins.append({
            "name": plugin.PLUGIN_NAME,
            "extensions": plugin.SUPPORTED_EXTENSIONS,
            "scan": plugin.scan_file,
            "target_types": getattr(plugin, "TARGET_TYPES", []),
            "embedders": getattr(plugin, "SUPPORTED_EMBEDDERS", []),
            "module": plugin,
        })

    return plugins


# Built-in transformation plugins.
from . import python

PLUGINS = {
    "python": python,
}

def get_transformation_plugin(path, target=None):
    """
    Resolve a transformation plugin.

    If target is supplied, preserve legacy --lang behavior.
    Otherwise resolve by file extension.

    Only plugins implementing transform_line() qualify as
    transformation plugins.
    """

    extension = path.suffix.lower()

    # --------------------------------------------------
    # Explicit target: legacy --lang behavior
    # --------------------------------------------------

    if target is not None:
        plugin = PLUGINS.get(target)

        if plugin is None:
            return None

        supported = getattr(plugin, "SUPPORTED_EXTENSIONS", [])

        if extension not in supported:
            return None

        if not hasattr(plugin, "transform_line"):
            return None

        return plugin

    # --------------------------------------------------
    # Automatic resolution by extension
    # --------------------------------------------------

    # Built-in transformation plugins first.
    for plugin in PLUGINS.values():

        supported = getattr(plugin, "SUPPORTED_EXTENSIONS", [])

        if extension not in supported:
            continue

        if hasattr(plugin, "transform_line"):
            return plugin

    # External plugins.
    for plugin in load_plugins():

        if extension not in plugin["extensions"]:
            continue

        module = plugin.get("module")

        if module is not None and hasattr(module, "transform_line"):
            return module

    return None