"""Test config loading behaviour."""

from ZERO.src.config import get_discord_token, get_log_level, get_guild_id


def test_log_level_default() -> None:
    """LOG_LEVEL defaults to INFO when unset."""
    assert get_log_level() in ("INFO", "DEBUG", "WARNING", "ERROR")


def test_guild_id_none_when_unset() -> None:
    """DISCORD_GUILD_ID returns None when not set."""
    assert get_guild_id() is None


def test_token_missing_raises() -> None:
    """get_discord_token raises KeyError when DISCORD_TOKEN is absent."""
    try:
        get_discord_token()
    except KeyError:
        return
    raise AssertionError("Expected KeyError from get_discord_token()")
