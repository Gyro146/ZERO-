"""Built-in commands for ZERO — registration only.

Import this module from bot.py before the bot logs in so all commands are
registered before the first /sync.  Individual command functions live in
submodules under src/commands/.
"""

from ZERO.src.commands.ping import register_ping
from ZERO.src.commands.ping import register_ping as _  # keep import side-effect clear


def register_all(bot) -> None:
    """Register all built-in commands onto the given bot instance."""
    register_ping(bot)
