"""Message event handler — expand as needed."""

import logging

from discord.ext import commands


def register_message_handler(bot: commands.Bot) -> None:
    """Attach the on_message listener.

    NOTE: discord.py bot.process_commands is automatically called when using
    @bot.event on_message.  If you add custom message logic here, make sure
    to still let the bot process commands (the decorator handles it).
    """

    @bot.event
    async def on_message(message) -> None:
        # Ignore the bot's own messages
        if message.author == bot.user:
            return

        log = logging.getLogger("ZERO")
        log.debug("Message from %s in %s: %s", message.author, message.guild, message.content)

        # Future: custom message processing here
