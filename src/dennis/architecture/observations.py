"""
Architecture Observation Definitions v0.1
"""

ARCHITECTURE_OBSERVATIONS = {

    "ARCHITECTURE.MODULE_PACKAGE_COLLISION": {
        "description":
            "A module file and package directory "
            "share the same import name.",

        "required_evidence": [
            "module_file",
            "package_dir",
        ],

        "confidence": 1.0,
    },

    "ARCHITECTURE.OVERSIZED_MODULE": {
        "description":
            "A source file exceeds the configured "
            "size threshold.",

        "required_evidence": [
            "file",
            "line_count",
        ],
    },

    "ARCHITECTURE.DUPLICATE_AST_CANDIDATE": {
        "description":
            "Two functions have identical or highly "
            "similar AST structure.",

        "required_evidence": [
            "symbol_a",
            "symbol_b",
            "similarity",
        ],
    },

    "ARCHITECTURE.DEAD_FILE_CANDIDATE": {
        "description":
            "A file appears to have no references.",

        "required_evidence": [
            "file",
            "referenced_by",
        ],
    },
}