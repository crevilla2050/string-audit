def build_evidence_store(findings):

    evidence_store = {}

    for finding in findings:

        evidence = finding["evidence"]

        evidence_store[
            evidence["normalized_hash"]
        ] = evidence

    return evidence_store