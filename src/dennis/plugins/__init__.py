# src/dennis/plugins/__init__.py

from pathlib import Path
import importlib.util
from collections import defaultdict


PLUGIN_DIR = Path.home() / ".dennis" / "plugins"



class PluginResolutionError(Exception):
    """Raised when scanner plugins cannot be resolved unambiguously."""


def resolve_plugins(plugins, use_default_plugins=False):
    """Resolve scanner plugins independently for each extension.

    User plugins win by default. With use_default_plugins=True, built-ins
    win for extensions they support. Conflicting user claims always fail.
    """
    user_claims = defaultdict(list)
    builtin_claims = defaultdict(list)

    for plugin in plugins:
        source = plugin.get("source")
        if source not in {"user", "builtin"}:
            raise PluginResolutionError(
                f"Plugin {plugin.get('name', '<unnamed>')!r} has no valid source."
            )

        claims = user_claims if source == "user" else builtin_claims
        for extension in plugin["extensions"]:
            claims[extension].append(plugin)

    conflicts = {
        extension: sorted(item["name"] for item in claimants)
        for extension, claimants in user_claims.items()
        if len(claimants) > 1
    }
    if conflicts:
        details = "; ".join(
            f"{extension}: {', '.join(names)}"
            for extension, names in sorted(conflicts.items())
        )
        raise PluginResolutionError(
            f"Conflicting user scanner plugins ({details}). "
            "Resolve these conflicts before scanning."
        )

    winners = {}
    for extension in sorted(set(user_claims) | set(builtin_claims)):
        users = user_claims.get(extension, [])
        builtins = builtin_claims.get(extension, [])

        if use_default_plugins and builtins:
            candidates = builtins
        elif users:
            candidates = users
        else:
            candidates = builtins

        for candidate in candidates:
            identity = (
                candidate["name"],
                candidate["source"],
                id(candidate["scan"]),
            )
            if identity not in winners:
                resolved = dict(candidate)
                resolved["extensions"] = []
                winners[identity] = resolved
            winners[identity]["extensions"].append(extension)

    result = []
    for item in winners.values():
        item["extensions"] = tuple(sorted(item["extensions"]))
        result.append(item)

    return sorted(result, key=lambda item: (item["name"], item["source"]))


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
    """Discover built-in scanner plugins and installed user plugins.

    Scanner plugins expose ``PLUGIN_NAME``, ``SUPPORTED_EXTENSIONS`` and
    ``scan_file(path, lines)``. Transformation plugins remain a separate
    interface and are resolved by ``get_transformation_plugin`` below.
    """

    from . import html, office_documents

    def record(module, source):
        return {
            "name": module.PLUGIN_NAME,
            "extensions": tuple(
                str(extension).lower()
                for extension in module.SUPPORTED_EXTENSIONS
            ),
            "scan": module.scan_file,
            "target_types": getattr(module, "TARGET_TYPES", []),
            "embedders": getattr(module, "SUPPORTED_EMBEDDERS", []),
            "module": module,
            "source": source,
        }

    plugins = [
        record(html, "builtin"),
        record(office_documents, "builtin"),
    ]

    if not PLUGIN_DIR.exists():
        return plugins

    for path in sorted(PLUGIN_DIR.glob("*.py")):
        # Ignore private/helper files.
        if path.name.startswith("_"):
            continue

        module = _load_plugin_file(path)
        if module is None:
            continue

        plugins.append(record(module, "user"))

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