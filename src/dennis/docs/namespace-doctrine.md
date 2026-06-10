# Namespace Doctrine

All observation types, goals, specifications, and future semantic artifacts MUST use namespaces from their first public version.

Namespaces exist to prevent collisions between domains and to make artifact intent self-describing.

Examples:

```
STRING.HUMAN
STRING.SQL
STRING.URL

ARCHITECTURE.MODULE_PACKAGE_COLLISION
ARCHITECTURE.OVERSIZED_MODULE
ARCHITECTURE.DUPLICATE_FUNCTION_CANDIDATE

SECURITY.HARDCODED_SECRET
SECURITY.WEAK_HASH_ALGORITHM
```

A namespace represents the observation domain, while the identifier represents the specific observation.

New observation categories MUST introduce a namespace rather than creating global identifiers.

Avoid:

```
MODULE_PACKAGE_COLLISION
OVERSIZED_MODULE
DUPLICATE_FUNCTION_CANDIDATE
```

Prefer:

```
ARCHITECTURE.MODULE_PACKAGE_COLLISION
ARCHITECTURE.OVERSIZED_MODULE
ARCHITECTURE.DUPLICATE_FUNCTION_CANDIDATE
```

This rule applies to future Goal Discovery and Spec Discovery layers as well.

The objective is long-term stability, collision avoidance, and self-describing artifacts.
