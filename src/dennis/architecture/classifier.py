"""
Architecture classification rules.

Converts observations into higher-level
architecture interpretations.

Version:
    v0.1
"""

from dennis.architecture.catalog import (
    CLASSIFICATIONS
)


INTERFACE_METHODS = {
    "execute",
    "fetchone",
    "fetchall",
    "begin",
    "commit",
    "rollback",
    "close",
}


def classify_duplicate_candidate(finding):
    """
    Classify a duplicate AST finding.

    Parameters
    ----------
    finding : dict
        ARCHITECTURE.DUPLICATE_AST_CANDIDATE
        observation.

    Returns
    -------
    dict
        Classification result.
    """

    funcs = finding["evidence"]["functions"]

    names = {
        f["name"]
        for f in funcs
    }

    files = {
        f["file"]
        for f in funcs
    }

    #
    # Rule 1:
    # Storage backend implementations.
    #

    if (
        len(names) == 1
        and next(iter(names))
            in INTERFACE_METHODS
        and all(
            "/storage/"
            in path.replace("\\", "/")
            for path in files
        )
    ):

        return {
            "classification":
                "INTERFACE_IMPLEMENTATION",

            "confidence":
                0.90,

            "metadata":
                CLASSIFICATIONS[
                    "INTERFACE_IMPLEMENTATION"
                ],
        }

    #
    # Rule 2:
    # Abstract contract.
    #

    if (

        len(names) >= 3

        and len(files) == 1

        and all(
            "/storage/base.py"
            in path.replace("\\", "/")
            for path in files
        )

    ):

        return {

            "classification":
                "ABSTRACT_CONTRACT",

            "confidence":
                0.99,

            "metadata":
                CLASSIFICATIONS[
                    "ABSTRACT_CONTRACT"
                ],
        }


    #
    # Rule 3:
    # Shared utility candidate.
    #

    if (
        len(funcs) >= 3
        and len(files) >= 3
    ):

        return {
            "classification":
                "SHARED_UTILITY_CANDIDATE",

            "confidence":
                0.95,

            "metadata":
                CLASSIFICATIONS[
                    "SHARED_UTILITY_CANDIDATE"
                ],
        }

    #
    # Fallback.
    #

    return {
        "classification":
            "UNKNOWN_DUPLICATION",

        "confidence":
            0.50,

        "metadata":
            CLASSIFICATIONS[
                "UNKNOWN_DUPLICATION"
            ],
    }
