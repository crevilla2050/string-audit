from pathlib import Path
import importlib.util

def load_plugins():
    plugins = []

    plugin_dir = Path.home() / ".dennis/plugins"

    if not plugin_dir.exists():
        return plugins

    for file in plugin_dir.glob("*.py"):

        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception:
            continue  # skip broken plugin

        # minimal validation
        if not hasattr(module, "PLUGIN_NAME"):
            continue
        if not hasattr(module, "SUPPORTED_EXTENSIONS"):
            continue
        if not hasattr(module, "scan_file"):
            continue

        plugins.append({
            "name": module.PLUGIN_NAME,
            "extensions": module.SUPPORTED_EXTENSIONS,
            "scan": module.scan_file,
            "target_types": getattr(module, "TARGET_TYPES", []),
            "embedders": getattr(module, "SUPPORTED_EMBEDDERS", []),
        })

    return plugins