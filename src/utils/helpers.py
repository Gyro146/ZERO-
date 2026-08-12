"""Utilities and helpers shared across the bot."""

from __future__ import annotations


def format_seconds(seconds: float) -> str:
    """Human-friendly duration string, e.g. '1h 23m 45s'."""
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)
