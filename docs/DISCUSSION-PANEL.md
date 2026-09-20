# Postdated article discussion panel

Ghost article template must use the Ghost post id to GET /public/discussions/articles/{ghost_post_id}. The response includes a Discord forum thread URL, assigned tags, title, excerpt and optional featured URL. A separate /public/discussions/community/{guild_id} endpoint returns a cached Discord server icon and counts (null means unavailable). Render user-facing text using textContent, never innerHTML. The button is Discord blurple #5865F2 with a white Discord SVG mark and opens the exact thread_url.

Security boundary: the public discussion table accepts writes only through authenticated /internal/discussions endpoints and only when forum_id is present in DISCORD_PUBLIC_FORUM_IDS. Do not ingest staff channels, staff forum threads, private message bodies, or generic bot audit logs into these endpoints. An allowlisted forum must also have Discord permissions granting @everyone access. The article endpoint does not expose message bodies. A future public reply bridge must verify channel visibility per message and apply moderation before publishing replies.

Required env: DISCORD_PUBLIC_FORUM_IDS (comma-separated Discord forum snowflake IDs). These endpoints are API foundations, not a finished Ghost theme or Ghost webhook integration.
