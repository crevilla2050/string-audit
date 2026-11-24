# Dennis CLI Trust reference — 0.9.4

`dennis dex attach-evidence ARTIFACT DOCUMENT` attaches an already obtained
Portable Trust Evidence document atomically.  `dennis dex issue-and-attach`
requests it from an HTTPS Tessa endpoint and attaches only after a complete,
valid response; errors leave the original artifact unchanged.

Use `dennis trust-root inspect RECORD` before pinning. Bootstrap with
`dennis trust-root pin RECORD --fingerprint SHA256`, where the fingerprint was
obtained independently of Tessa. Routine rotation requires a signature from
the currently active pinned root. Never use rotation for compromise recovery:
stop online trust use, obtain a replacement root fingerprint through an
independent channel, preserve the old records, and investigate before pinning.

Cryptographic evidence validity and current authority status are distinct.
Online-first verification obtains a signed current status. Offline fallback
can verify cached keys but cannot prove fresh revocation status.
