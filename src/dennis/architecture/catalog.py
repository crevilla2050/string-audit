CLASSIFICATIONS = {

    "INTERFACE_IMPLEMENTATION": {

        "description":
            (
                "Duplicate capability likely "
                "exists because multiple "
                "implementations satisfy "
                "the same contract."
            ),

        "severity":
            "info",

        "recommendation":
            (
                "No action required unless "
                "implementations begin to "
                "diverge unexpectedly."
            ),
    },

    "ABSTRACT_CONTRACT": {

        "description":
            (
                "Functions represent an "
                "abstract contract or base "
                "interface definition rather "
                "than duplicated business "
                "logic."
            ),

        "severity":
            "info",

        "recommendation":
            (
                "No action required. Verify "
                "that implementations remain "
                "consistent with the contract."
            ),
    },

    "SHARED_UTILITY_CANDIDATE": {

        "description":
            (
                "The same capability appears "
                "across multiple unrelated "
                "modules and may benefit from "
                "consolidation into a shared "
                "utility."
            ),

        "severity":
            "medium",

        "recommendation":
            (
                "Consider extracting the "
                "capability into a canonical "
                "shared utility and replacing "
                "duplicate implementations."
            ),
    },

    "UNKNOWN_DUPLICATION": {

        "description":
            (
                "Duplicate capability "
                "detected but no matching "
                "classification rule exists."
            ),

        "severity":
            "unknown",

        "recommendation":
            (
                "Review manually and "
                "consider creating a new "
                "classification rule."
            ),
    },
}