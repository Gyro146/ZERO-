"""Events — bot lifecycle hooks.

Import this module before the bot connects so the decorators are applied.
"""

import logging

from discord.ext import commands


def register_events(bot: commands.Bot) -> None:
    """Attach event handlers to the bot.

    In discord.py the @bot.event decorator mutates the bot at import time,
    so the actual event functions are defined at module level and this
    function exists mainly for explicit registration clarity.
    """

    @bot.event
    async def on_ready() -> None:
        log = logging.getLogger("ZERO")
        log.info("ZERO is online — %s (ID: %s)", bot.user, bot.user.id)
