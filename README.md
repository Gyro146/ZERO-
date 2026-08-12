# ZERO — personal Discord bot
# ============================
# Built with Python 3.12 + discord.py 2.x
#
# Setup
# ------
# 1. Create a `.env` file in the project root (see `.env.example`).
# 2. Install dependencies:  pip install -r requirements.txt
# 3. Run:  python -m ZERO.src.bot
#
# Discord portal
# --------------
# - Enable the **Message Content** intent (for `!prefix` commands).
# - Enable the **Server Members** intent (optional, for member events later).
# - Copy the bot token into `.env` as `DISCORD_TOKEN`.
#
# Commands
# ---------
# - `/ping`  — slash health check
# - `!ping`  — prefix health check
#
# Configuration
# -------------
# Environment variables (set in `.env` or the host environment):
#
#   DISCORD_TOKEN     Bot token (required)
#   DISCORD_GUILD_ID  Optional guild ID — scopes slash commands to one server
#   LOG_LEVEL         DEBUG / INFO / WARNING / ERROR (default: INFO)
#
# Do NOT commit `.env` — it is gitignored.  Only `.env.example` is tracked.
#
# Development
# -----------
# - Lint:  ruff check .
# - Typecheck: mypy src/
# - Test:  pytest
