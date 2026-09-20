# One-command guided deployment from your computer

This installs the **development** Discord bot and GhostLive API on a dedicated Ubuntu 24.04 VPS. It does not deploy Ghost or the media transcoder to that VPS.

Download or clone the repository onto your computer, install Python 3.12+, then run:

```bash
python -m pip install -r scripts/requirements.txt
python scripts/deploy_discord.py --host YOUR_BOT_VPS_IP
```

The script prompts locally for the temporary SSH password (hidden), prints the SSH host key fingerprint for you to verify against your VPS provider console, and prompts for the Discord token, guild ID, channel IDs and editor role ID. It installs Docker and Git, clones/updates Ghostpack, writes a root-only remote .env, starts the live API and bot, runs unit tests, checks syntax and verifies the local API and bot container. The script does **not** save credentials to your computer or commit them to GitHub. The bot token and API token are stored in the VPS's /opt/ghostpack/.env; protect this file and backups.

The script requires an Ubuntu account with passwordless sudo or root access. SSH-key authentication is available with --key PATH (currently RSA key files). The first-connection host fingerprint must be verified out of band; do not type TRUST without checking it. If your VPS provider disables password SSH, configure an SSH key through its console. Do not paste credentials into ChatGPT.

This is not a production launch: Discord gateway authentication and command permissions require a live integration test; the bot still lacks Ghost publishing, media processing, and end-of-event confirmation. Rotate the temporary VPS password after successful setup. Use the provider console if SSH becomes unavailable.
