# Postdated article discussion panel

Ghost article template must use the Ghost post id to GET /public/discussions/articles/{ghost_post_id}. The response includes a Discord forum thread URL, assigned tags, title, excerpt and optional featured URL. A separate /public/discussions/community/{guild_id} endpoint returns a cached Discord server icon and counts (null means unavailable). Render user-facing text using textContent, never innerHTML. The button is Discord blurple #5865F2 with a white Discord SVG mark and opens the exact thread_url.

Security boundary: the public discussion table accepts writes only through authenticated /internal/discussions endpoints and only when forum_id is present in DISCORD_PUBLIC_FORUM_IDS. Do not ingest staff channels, staff forum threads, private message bodies, or generic bot audit logs into these endpoints. An allowlisted forum must also have Discord permissions granting @everyone access. The article endpoint does not expose message bodies. A future public reply bridge must verify channel visibility per message and apply moderation before publishing replies.

Required env: DISCORD_PUBLIC_FORUM_IDS (comma-separated Discord forum snowflake IDs). These endpoints are API foundations, not a finished Ghost theme or Ghost webhook integration.

## Ghost theme integration (implemented widget, installation pending)

Copy theme/assets/js/ghostpack-discussion.js into your Ghost theme's assets/js directory and include it in the post template. Example Handlebars (replace YOUR_GUILD_ID with your Discord guild snowflake):

```hbs
{{#post}}
<div class="ghostpack-discussion"
  data-post-id="{{id}}"
  data-guild-id="YOUR_GUILD_ID"
  data-api-base="https://ghostbot.postdated.org"></div>
<script defer src="{{asset "js/ghostpack-discussion.js"}}"></script>
{{/post}}
```

The button displays the official white Discord mark on #5865F2, the actual cached server icon, assigned article tags, total members, online count if available, and boosts. It opens the article-specific forum thread. Do not use the sample API hostname until HTTPS and the reverse proxy expose ONLY /public/discussions/* for public access; keep /internal/* and all editorial endpoints private. If no discussion exists the widget hides rather than linking to the wrong article. This JS file is not yet installed into an actual Ghost theme or deployed.

Discord's default forum thread permissions must allow public reading. The sync job requires DISCORD_ARTICLES_FORUM_ID and DISCORD_PUBLIC_FORUM_IDS to include that same forum ID; it polls Ghost every 15 minutes. Configure GHOST_AUTHOR_DISCORD_IDS as a JSON object mapping Ghost author IDs to Discord member IDs for author mentions. Online count is intentionally null until a supported accurate measurement is implemented.
