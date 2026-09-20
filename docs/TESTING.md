# Test plan

GitHub Actions performs Python syntax checks and available unit tests. A passing unit test does not establish that Discord, Ghost, FFmpeg codecs, uploads, storage adapters or video playback work end-to-end.

For local smoke testing, copy .env.example to .env and set MEDIA_TOKEN and LIVE_TOKEN. Run docker compose up --build media live. GET /health on localhost ports 8080 and 8090. Use the media API's authenticated /process endpoint with a small JPEG and a short MP4; confirm actual AVIF and AV1 output using ffprobe. Exercise live event creation, update submission, approval and private archive with a test token. Do not connect production Discord or Ghost until the remaining integration work and security review are complete.

The bot is opt-in: docker compose --profile discord up --build. It requires a Discord bot token, guild/channel IDs, editor role ID, Message Content intent and a functioning live API. The current bot does not persist thread mapping across restarts, so use only a test server.
