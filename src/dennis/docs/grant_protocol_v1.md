# Grant Protocol v1
## Dennis Universe Specification

Status: Draft
Version: 0.1

---

## Purpose

The Grant Protocol defines a universal mechanism for delegating temporary or permanent capabilities between trusted actors.
The protocol is intentionally independent from Dennis Forge and may be implemented by any Ilpresim product or third-party application.

Every Grant MAY declare its lineage. Lineage expresses the delegation from which the current Grant originates. It records causality, not chronology.

A Grant is not a user.
A Grant is not a session.
A Grant is not a membership.
A Grant is not an authentication token.
A Grant is a verifiable delegation of capability.
A Grant represents delegated trust between trusted actors.

## Origin

The Grant Protocol originated during the implementation of password recovery.

While designing the feature, it became apparent that password recovery, memberships, invitations, workspace sharing, feature activation, ownership transfer and many other authorization problems were all instances of the same underlying concept:

Delegated capability.

The protocol intentionally models that concept rather than any individual feature.

## First Principle

A Grant answers one question.

"What is this subject currently authorized to do?"

Nothing more.

Nothing less.

## A Grant does not

- authenticate identities
- execute operations
- replace business logic
- replace organizational policy
- replace audit systems
- replace workflows

Every capability granted by the system SHOULD be represented as a Grant whenever practical.

Examples

- Password recovery
- Email verification
- Trial access
- Membership
- Workspace invitation
- Ownership transfer
- API approval
- Premium storage
- Feature unlock

Capabilities belong to Grants.
Business meaning belongs to applications.
Forge does not sell memberships.
Forge issues Grants.

## Immutable History

A Grant is never rewritten.
A Grant evolves exclusively through Chronicle events.
Current state is derived from Chronicle.

The Grant Protocol intentionally treats memberships as a special case of delegated capability.

Implementations SHOULD avoid introducing parallel membership systems unless the capability model proves insufficient.

## Design Philosophy

The Grant Protocol intentionally models delegated authority rather than application-specific features.

Applications SHOULD express their business operations in terms of capabilities delegated by Grants instead of introducing specialized authorization mechanisms.

The protocol favors composition over specialization.

New use cases SHOULD first attempt to reuse existing Grant concepts before introducing new protocol primitives.

When in doubt:

Keep the Grant small.
Keep the Chronicle immutable.
Keep the Lineage explicit.
Keep the capability generic.