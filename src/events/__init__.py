import logging

from discord.ext import commands

from ZERO.src.events.on_ready import register_events
from ZERO.src.events.on_message import register_message_handler


def register_all(bot: commands.Bot) -> None:
    """Register all event handlers."""
    register_events(bot)
    register_message_handler(bot)
