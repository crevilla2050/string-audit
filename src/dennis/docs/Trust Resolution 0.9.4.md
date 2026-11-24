# Dennis 0.9.4 Trust Resolution

Dennis loads trust configuration from `~/.dennis/.env`. The default
`online-first` mode verifies embedded evidence cryptographically, queries
configured Tessa HTTPS trust endpoints in listed order, and uses the local
SQLite key registry only when every endpoint is unavailable.

`DENNIS_TRUST_MODE` is `online-first` or `offline-only`. `offline-only` never
opens a network connection. `DENNIS_TRUST_SERVERS` is a comma-separated,
HTTPS-only list. `DENNIS_TRUST_TIMEOUT_SECONDS` limits each request.

`DENNIS_TRUST_SQLITE_FALLBACK` controls use of `DENNIS_TRUST_DB_PATH`, which
defaults to `~/.dennis_keys.db`. SQLite fallback reports cached/offline trust,
not fresh online revocation status.

Optional `DENNIS_TRUST_CA_BUNDLE` selects a trust CA. Optional client mTLS
requires both `DENNIS_TRUST_CLIENT_CERT` and `DENNIS_TRUST_CLIENT_KEY`.
Private signing keys, DEX payloads, and artifact contents are never sent.

The approved public lookup protocol is `TESSA-TRUST-LOOKUP/1.0` at
`POST /api/v1/trust/keys/resolve`. Requests contain only `key_id` and an
optional evidence timestamp. Responses are JCS-signed Ed25519 authority
statements. Dennis rejects malformed, unsigned, expired, TLS-failed, and
conflicting responses. A valid online `REVOKED` or `UNTRUSTED` response never
falls back to SQLite.
