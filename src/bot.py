import asyncio
import logging
import sys
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ZERO.src.config import get_discord_token, get_log_level, get_guild_id


def setup_logging(level: str) -> logging.Logger:
    """Configure root logger with console handler. Returns the logger."""
    log = logging.getLogger("ZERO")
    log.setLevel(getattr(logging, level, logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    log.addHandler(handler)

    # Reduce noise from discord.py internals unless DEBUG
    if level == "DEBUG":
        logging.getLogger("discord").setLevel(logging.DEBUG)
    else:
        logging.getLogger("discord").setLevel(logging.WARNING)

    return log


# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True  # required for prefix (!) commands
intents.members = True          # optional: member join/leave events later

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,  # we handle help ourselves later
)


# ---------------------------------------------------------------------------
# Lifecycle events
# ---------------------------------------------------------------------------

@bot.event
async def on_ready() -> None:
    """Called when the bot has successfully connected and synced."""
    log = logging.getLogger("ZERO")
    log.info("ZERO is online — %s (ID: %s)", bot.user, bot.user.id)

    if guild_id := get_guild_id():
        guild = bot.get_guild(guild_id)
        if guild:
            log.info("Linked to guild: %s (ID: %s)", guild.name, guild.id)
        else:
            log.warning("DISCORD_GUILD_ID set but guild not found in cache.")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@bot.event
async def on_command_error(
    ctx: commands.Context, error: commands.CommandError
) -> None:
    """Handle prefix-command errors gracefully."""
    log = logging.getLogger("ZERO")

    if isinstance(error, commands.CommandNotFound):
        # Ignore unknown prefix commands — keeps logs clean
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to run that command.")
        return

    # Catch-all: log and tell the user something went wrong
    log.error(
        "Error in prefix command '%s' by %s: %s",
        ctx.command.qualified_name or "unknown",
        ctx.author,
        error,
        exc_info=True,
    )
    await ctx.send("Something went wrong while running that command.")


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    """Handle slash-command errors gracefully."""
    log = logging.getLogger("ZERO")

    if isinstance(error, app_commands.CommandNotFound):
        return  # shouldn't happen via the tree, but be safe

    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You don't have permission to run that command.", ephemeral=True
        )
        return

    if isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message(
            "I'm missing permissions to run that command.", ephemeral=True
        )
        return

    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"This command is on cooldown. Try again in {error.retry_after:.1f}s.",
            ephemeral=True,
        )
        return

    # Catch-all
    log.error(
        "Error in slash command '%s' by %s: %s",
        getattr(error, "command", "unknown") or interaction.command.qualified_name,
        interaction.user,
        error,
        exc_info=True,
    )
    try:
        await interaction.response.send_message(
            "Something went wrong while running that command.", ephemeral=True
        )
    except discord.InteractionResponded:
        try:
            await interaction.followup.send(
                "Something went wrong.", ephemeral=True
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Command registration & sync
# ---------------------------------------------------------------------------

async def sync_commands() -> None:
    """Sync application (slash) commands. Scoped to a single guild when
    DISCORD_GUILD_ID is set (faster); otherwise global sync."""
    log = logging.getLogger("ZERO")

    if guild_id := get_guild_id():
        guild = discord.Object(id=guild_id)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        log.info("Synced %d slash command(s) to guild %d.", len(synced), guild_id)
    else:
        synced = await bot.tree.sync()
        log.info("Synced %d slash command(s) globally.", len(synced))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main_async() -> None:
    level = get_log_level()
    log = setup_logging(level)

    log.info("Starting ZERO bot…")
    token = get_discord_token()

    # Register all commands onto the live bot instance before login
    from ZERO.src.commands import register_all
    register_all(bot)

    await bot.login(token)
    await sync_commands()
    await bot.connect()


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logging.getLogger("ZERO").info("Shutting down ZERO.")
    except Exception:
        logging.getLogger("ZERO").exception("Fatal error during startup. Shutting down.")
        raise


if __name__ == "__main__":
    main()
