# Discord bot VPS (development deployment)

Install Docker Engine and Docker Compose on the bot VPS. Clone the repository and copy .env.example to .env; chmod 600 .env. Configure DISCORD_TOKEN, DISCORD_GUILD_ID, the management/reporting/queue channel IDs, EDITOR_ROLE_ID, and LIVE_TOKEN. Keep LIVE_TOKEN identical between bot and live API. Enable Message Content intent in the Discord developer portal and grant the bot slash-command, thread, message and reaction permissions.

For a single VPS, run `docker compose --profile discord up -d --build live bot`. This starts a local live API plus the Discord bot. The live API binds to 127.0.0.1:8090 and is not publicly accessible by default. Do not expose the API or the bot token. For separate VPS instances, replace LIVE_API_URL with a private VPN/TLS address, configure the live API's own persistent volume, and keep bearer tokens secret.

**Important:** This is a development deployment only. The current Discord adapter still needs persistent thread lookup, robust retry handling, private attachment ingestion wiring, editor revision UX, explicit /end confirmation, Ghost publication and archive delivery before it is suitable for newsroom use. Do not submit sensitive reporting until these are completed and tested.
