import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _env_path() -> Path:
    """Resolve .env path relative to the project root (ZERO/)."""
    return Path(__file__).resolve().parents[1] / ".env"


def _load_env():
    """Load .env if python-dotenv is available and the file exists."""
    if load_dotenv is not None:
        load_dotenv(_env_path(), override=False)


def get_discord_token() -> str:
    """Return the Discord bot token. Raises KeyError if missing."""
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise KeyError(
            "DISCORD_TOKEN is not set. "
            "Set it in a .env file at the project root or as an environment variable."
        )
    return token


def get_log_level() -> str:
    """Return the log level string, defaulting to INFO."""
    return os.environ.get("LOG_LEVEL", "INFO").upper()


def get_guild_id() -> Optional[int]:
    """Optional guild ID for targeted command sync/testing."""
    raw = os.environ.get("DISCORD_GUILD_ID")
    if raw:
        try:
            return int(raw)
        except ValueError:
            return None
    return None


# Ensure .env is loaded before any config reads happen.
_load_env()
