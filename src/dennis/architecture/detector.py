from pathlib import Path


def module_name_from_path(path: Path, root: Path) -> str:
    """
    Convert:

        src/dennis/plugins.py

    into:

        dennis.plugins

    and:

        src/dennis/plugins/

    into:

        dennis.plugins
    """

    relative = path.relative_to(root)

    parts = list(relative.parts)

    if path.is_file():

        if parts[-1] == "__init__.py":
            parts.pop()

        else:
            parts[-1] = path.stem

    return ".".join(parts)


def detect_module_package_collisions(root):

    findings = []

    root = Path(root)

    modules = {}
    packages = {}

    for py_file in root.rglob("*.py"):

        if py_file.name == "__init__.py":
            continue

        fq_name = module_name_from_path(
            py_file,
            root
        )

        modules[fq_name] = str(py_file)

    for directory in root.rglob("*"):

        if not directory.is_dir():
            continue

        init_file = directory / "__init__.py"

        if init_file.exists():

            fq_name = module_name_from_path(
                directory,
                root
            )

            packages[fq_name] = str(directory)

    for name in sorted(
        set(modules) & set(packages)
    ):
        
        findings.append(
            {
                "type":
                    "ARCHITECTURE.MODULE_PACKAGE_COLLISION",

                "evidence": {
                    "module_file":
                        modules[name],

                    "package_dir":
                        packages[name],
                },

                "confidence": 1.0,
            }
        )
    
    return findings