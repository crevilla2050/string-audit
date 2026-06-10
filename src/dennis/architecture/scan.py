from dennis.architecture.ast_compare import (
    detect_duplicate_ast_candidates
)

from dennis.architecture.catalog_builder import (
    build_catalog
)

from dennis.architecture.index_builder import (
    build_observation_index
)

from dennis.architecture.evidence_builder import (
    build_evidence_store
)

from dennis.architecture.export import (
    save_observation_index,
    save_evidence_store,
    timestamp
)

def run_architecture_scan(
    source_path,
    output_format="json"
):
    """
    Scan source tree and generate
    architecture observations.
    """

    findings = (
        detect_duplicate_ast_candidates(
            source_path
        )
    )

    #
    # Force catalog generation.
    #
    # Even if not persisted yet,
    # this validates classifications.
    #

    build_catalog(
        findings
    )

    index = build_observation_index(
        findings
    )

    evidence = build_evidence_store(
        findings
    )

    ts = timestamp()

    index_file = (
        save_observation_index(
            index,
            source_path,
            ts
        )
    )

    evidence_file = (
        save_evidence_store(
            evidence,
            source_path,
            ts
        )
    )

    print(
        "[Dennis] Architecture "
        "scan complete."
    )

    print(
        f"[Dennis] Observation "
        f"index: {index_file}"
    )

    print(
        f"[Dennis] Evidence "
        f"store: {evidence_file}"
    )

    print(
        f"[Dennis] Findings: "
        f"{len(findings)}"
    )