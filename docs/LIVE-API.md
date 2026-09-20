# GhostLive development API
The API provides authenticated event creation, submissions, revisions, editorial decisions with version checks, publication acknowledgment and a private JSON audit export. Set LIVE_TOKEN to a strong secret. The client must enforce authorized reporter/editor roles: bearer access alone is not a role system. The current SQLite store is single-instance only. Do not expose the API to the public internet without TLS and an authenticated gateway.

No Discord bot, Ghost post creation, actual Ghost publication, or media attachment ingestion is wired to this API yet. The /published endpoint is an acknowledgment, not a Ghost publisher. Archives include held and unpublished submissions and MUST remain private.
