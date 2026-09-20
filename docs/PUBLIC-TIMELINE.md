# Public GhostLive timeline API

The read-only endpoint GET /public/events/{event_id} returns only updates with state=published for events associated with a Ghost post. It excludes private media references, reporter IDs, editor IDs, pending submissions, held submissions and approved-but-not-yet-published submissions. The event association endpoint POST /events/{event_id}/ghost requires LIVE_TOKEN.

IMPORTANT: Association to a Ghost post ID is not proof that the post is actually public. Only associate a post after confirming Ghost has published it. A public API exposed via reverse proxy must route ONLY /public/ paths; never expose /events/, /updates/ or /threads/ without authentication. Implement pagination, moderation controls, CDN caching, rate limits and a Ghost theme integration before production use.
