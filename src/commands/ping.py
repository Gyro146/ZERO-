"""Ping / Pong — the canonical health-check command.

Registered as BOTH:
  - Slash  command: /ping
  - Prefix command: !ping
"""

from discord import app_commands
import discord
from discord.ext import commands


def register_ping(bot: commands.Bot) -> None:
    """Attach /ping and !ping to the bot."""

    # --- Slash command -------------------------------------------------------
    @bot.tree.command(name="ping", description="Check if ZERO is alive.")
    async def _ping(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Pong!")

    # --- Prefix command ------------------------------------------------------
    @bot.command(name="ping", aliases=("pong",))
    async def _ping_prefix(ctx: commands.Context) -> None:
        await ctx.send("Pong!")
