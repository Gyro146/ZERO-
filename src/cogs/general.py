"""Cog placeholder — expand with feature cogs later."""

from discord.ext import commands


class GeneralCog(commands.Cog, name="General"):
    """Placeholder cog — replace with real feature modules."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        pass


async def setup(bot: commands.Bot) -> None:
    """Required signature for bot.load_extension('ZERO.src.cogs.general')."""
    await bot.add_cog(GeneralCog(bot))
