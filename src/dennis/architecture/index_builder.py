from dennis.architecture.classifier import (
    classify_duplicate_candidate
)


def build_observation_index(findings):

    index = {
        "findings": []
    }

    for finding in findings:

        result = classify_duplicate_candidate(
            finding
        )

        evidence = finding["evidence"]

        index["findings"].append(
            {
                "classification":
                    result[
                        "classification"
                    ],

                "confidence":
                    result[
                        "confidence"
                    ],

                "evidence_hash":
                    evidence[
                        "normalized_hash"
                    ],
            }
        )

    return index