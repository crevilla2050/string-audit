"""
Architecture catalog builder.

Groups classified findings into a
higher-level architecture catalog.

Version:
    v0.1
"""

from collections import defaultdict

from dennis.architecture.classifier import (
    classify_duplicate_candidate
)


def build_catalog(findings):
    """
    Build an architecture catalog.

    Parameters
    ----------
    findings : list
        Architecture observations.

    Returns
    -------
    dict
        Catalog structure.
    """

    catalog = {
        "meta": {
            "format":
                "architecture-catalog",

            "version":
                1,
        },

        "classifications":
            defaultdict(list),
    }

    for finding in findings:

        result = classify_duplicate_candidate(
            finding
        )

        evidence = finding["evidence"]

        catalog[
            "classifications"
        ][
            result["classification"]
        ].append(
            {
                "normalized_hash":
                    evidence[
                        "normalized_hash"
                    ],

                "functions":
                    [
                        f["name"]
                        for f in evidence[
                            "functions"
                        ]
                    ],

                "confidence":
                    result[
                        "confidence"
                    ],
            }
        )

    catalog[
        "classifications"
    ] = dict(
        catalog[
            "classifications"
        ]
    )

    return catalog