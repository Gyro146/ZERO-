"""Ticket configuration cog — admin-only Discord-based management.

Command names (all ≤32 chars, lowercase/numbers/hyphens/underscores):

Category management (admin only):
  /ticket-category-add[name,description]       — Create category
  /ticket-category-edit[id,name?,description?] — Edit category
  /ticket-category-remove[id]                  — Delete category
  /ticket-category-list                        — List all categories
  /ticket-category-toggle[id]                  — Enable/disable
  /ticket-category-reorder                     — Reorder via dropdown

Settings (admin only):
  /ticket-config                               — View settings
  /ticket-config-admin[roles]                 — Set admin roles
  /ticket-config-staff[roles]                 — Set staff roles
  /ticket-config-panel[channel]               — Set panel channel
  /ticket-config-active[category]             — Set active tickets category
  /ticket-config-closed[category]             — Set closed tickets category
  /ticket-config-log[channel]                 — Set log channel
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ZERO.src.utils.storage import (
    add_category,
    get_categories,
    get_enabled_categories,
    get_settings,
    remove_category,
    reorder_category,
    toggle_category,
    update_category,
    update_settings,
)


def _is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user has any of the configured admin roles, or is the bot owner."""
    settings = get_settings()
    admin_ids = set(settings.get("admin_role_ids", []))
    if not admin_ids:
        return (
            interaction.user.id == interaction.client.owner_id
            if interaction.client.owner_id
            else False
        )
    user_roles = {r.id for r in interaction.user.roles}
    return bool(user_roles & admin_ids)


def _is_staff(interaction: discord.Interaction) -> bool:
    """Check if the user has any of the configured staff roles (or is admin)."""
    if _is_admin(interaction):
        return True
    settings = get_settings()
    staff_ids = set(settings.get("staff_role_ids", []))
    if not staff_ids:
        return False
    user_roles = {r.id for r in interaction.user.roles}
    return bool(user_roles & staff_ids)


# ---------------------------------------------------------------------------
# Category commands
# ---------------------------------------------------------------------------

class TicketConfigCog(commands.Cog, name="Ticket Configuration"):
    """Manage ticket categories and settings — admin-only."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # --- Add category ----------------------------------------------------------

    @app_commands.command(name="ticket-category-add",
                          description="Create a new ticket category")
    @app_commands.check(_is_admin)
    async def category_add(
        self,
        interaction: discord.Interaction,
        name: str,
        description: str = "",
    ) -> None:
        try:
            cat = add_category(name, description)
            await interaction.response.send_message(
                f"✅ Created category **{cat['name']}** (`{cat['id']}`)",
                ephemeral=True,
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    # --- Edit category --------------------------------------------------------

    @app_commands.command(name="ticket-category-edit",
                          description="Edit an existing ticket category")
    @app_commands.check(_is_admin)
    async def category_edit(
        self,
        interaction: discord.Interaction,
        category_id: str,
        name: str = "",
        description: str = "",
    ) -> None:
        if not name and not description:
            await interaction.response.send_message(
                "❌ Provide at least a new `name` or `description`.", ephemeral=True
            )
            return
        try:
            updated = update_category(
                category_id,
                name=name if name else None,
                description=description if description else None,
            )
            if updated is None:
                await interaction.response.send_message(
                    f"❌ Category `{category_id}` not found.", ephemeral=True
                )
                return
            changes = []
            if name:
                changes.append(f"name → **{updated['name']}**")
            if description:
                changes.append(f"description → {updated['description']!r}")
            await interaction.response.send_message(
                f"✅ Updated `{updated['id']}`: {', '.join(changes)}", ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    # --- Remove category ------------------------------------------------------

    @app_commands.command(name="ticket-category-remove",
                          description="Delete a ticket category")
    @app_commands.check(_is_admin)
    async def category_remove(
        self,
        interaction: discord.Interaction,
        category_id: str,
    ) -> None:
        if remove_category(category_id):
            await interaction.response.send_message(
                f"✅ Removed category `{category_id}`.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Category `{category_id}` not found.", ephemeral=True
            )

    # --- List categories ------------------------------------------------------

    @app_commands.command(name="ticket-category-list",
                          description="List all ticket categories")
    @app_commands.check(_is_staff)
    async def category_list(
        self,
        interaction: discord.Interaction,
    ) -> None:
        categories = get_categories()
        if not categories:
            await interaction.response.send_message(
                "No categories configured.", ephemeral=True
            )
            return
        lines = []
        for c in sorted(categories, key=lambda x: x.get("position", 0)):
            status = "✅" if c.get("enabled", True) else "⛔"
            lines.append(f"{status} `{c['id']}` — **{c['name']}**")
            if c.get("description"):
                lines.append(f"   _{c['description']}_")
        await interaction.response.send_message(
            "## Ticket Categories\n\n" + "\n".join(lines), ephemeral=True
        )

    # --- Toggle category ------------------------------------------------------

    @app_commands.command(name="ticket-category-toggle",
                          description="Enable or disable a category")
    @app_commands.check(_is_admin)
    async def category_toggle(
        self,
        interaction: discord.Interaction,
        category_id: str,
    ) -> None:
        cat = toggle_category(category_id)
        if cat is None:
            await interaction.response.send_message(
                f"❌ Category `{category_id}` not found.", ephemeral=True
            )
            return
        status = "enabled" if cat.get("enabled", True) else "disabled"
        await interaction.response.send_message(
            f"✅ `{cat['id']} — {cat['name']}` is now **{status}**.", ephemeral=True
        )

    # --- Reorder categories ---------------------------------------------------

    @app_commands.command(name="ticket-category-reorder",
                          description="Reorder ticket categories via a dropdown")
    @app_commands.check(_is_admin)
    async def category_reorder(
        self,
        interaction: discord.Interaction,
    ) -> None:
        categories = get_categories()
        if len(categories) < 2:
            await interaction.response.send_message(
                "Need at least 2 categories to reorder.", ephemeral=True
            )
            return
        view = ReorderView(categories)
        await interaction.response.send_message(
            "## Reorder Categories\nSelect a category, then use the second dropdown to pick its new position.",
            view=view,
            ephemeral=True,
        )


# ---------------------------------------------------------------------------
# Settings commands
# ---------------------------------------------------------------------------

    @app_commands.command(name="ticket-config",
                          description="View current ticket settings")
    @app_commands.check(_is_staff)
    async def view_settings(
        self,
        interaction: discord.Interaction,
    ) -> None:
        settings = get_settings()
        lines = [
            "## Ticket Settings\n",
            f"**Admin roles:** "
            + (", ".join(f"<@&{r}>" for r in settings.get("admin_role_ids", []))
               or "Not configured"),
            f"**Staff roles:** "
            + (", ".join(f"<@&{r}>" for r in settings.get("staff_role_ids", []))
               or "Not configured"),
            f"**Panel channel:** "
            + (f"<#{settings['panel_channel_id']}>"
               if settings.get("panel_channel_id") else "Not set"),
            f"**Active tickets category:** "
            + (f"<#{settings['active_category_id']}>"
               if settings.get("active_category_id") else "Not set"),
            f"**Closed tickets category:** "
            + (f"<#{settings['closed_category_id']}>"
               if settings.get("closed_category_id") else "Not set"),
            f"**Log channel:** "
            + (f"<#{settings['ticket_log_channel_id']}>"
               if settings.get("ticket_log_channel_id") else "Not set"),
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="ticket-config-admin",
                          description="Set admin roles for ticket configuration")
    @app_commands.check(_is_admin)
    async def set_admin_roles(
        self,
        interaction: discord.Interaction,
        roles: discord.Role,
    ) -> None:
        update_settings(admin_role_ids=[roles.id])
        await interaction.response.send_message(
            f"✅ Admin roles set to `<@&{roles.id}>`.", ephemeral=True
        )

    @app_commands.command(name="ticket-config-staff",
                          description="Set staff roles that can manage tickets")
    @app_commands.check(_is_admin)
    async def set_staff_roles(
        self,
        interaction: discord.Interaction,
        roles: discord.Role,
    ) -> None:
        update_settings(staff_role_ids=[roles.id])
        await interaction.response.send_message(
            f"✅ Staff roles set to `<@&{roles.id}>`.", ephemeral=True
        )

    @app_commands.command(name="ticket-config-panel",
                          description="Set the channel where the ticket panel lives")
    @app_commands.check(_is_admin)
    async def set_panel_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        update_settings(panel_channel_id=channel.id)
        await interaction.response.send_message(
            f"✅ Panel channel set to `<#{channel.id}>`.", ephemeral=True
        )

    @app_commands.command(name="ticket-config-active",
                          description="Set the Discord category for active tickets")
    @app_commands.check(_is_admin)
    async def set_active_category(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
    ) -> None:
        update_settings(active_category_id=category.id)
        await interaction.response.send_message(
            f"✅ Active tickets category set to `<#{category.id}>`.", ephemeral=True
        )

    @app_commands.command(name="ticket-config-closed",
                          description="Set the Discord category for closed/archived tickets")
    @app_commands.check(_is_admin)
    async def set_closed_category(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
    ) -> None:
        update_settings(closed_category_id=category.id)
        await interaction.response.send_message(
            f"✅ Closed tickets category set to `<#{category.id}>`.", ephemeral=True
        )

    @app_commands.command(name="ticket-config-log",
                          description="Set the channel for ticket event logs")
    @app_commands.check(_is_admin)
    async def set_log_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        update_settings(ticket_log_channel_id=channel.id)
        await interaction.response.send_message(
            f"✅ Log channel set to `<#{channel.id}>`.", ephemeral=True
        )


# ---------------------------------------------------------------------------
# Reorder dropdown view
# ---------------------------------------------------------------------------

class ReorderView(discord.ui.View):
    """Two-step dropdown for reordering categories."""

    def __init__(self, categories: list[dict]):
        super().__init__(timeout=120)
        self.categories = categories
        self._selected_id: str | None = None
        self._build_first_select()

    def _build_first_select(self) -> None:
        """Category selection dropdown."""
        self.clear_items()
        select = discord.ui.Select(
            placeholder="Select a category to move",
            min_values=1,
            max_values=1,
        )
        for c in sorted(self.categories, key=lambda x: x.get("position", 0)):
            select.add_option(
                label=c["name"],
                value=c["id"],
                description=f"Position {c.get('position', 0)} — {c.get('description', '')}",
            )
        select.callback = self._on_category_selected
        self.add_item(select)

    async def _on_category_selected(self, interaction: discord.Interaction) -> None:
        self._selected_id = self.children[0].values[0]
        cat = next((c for c in self.categories if c["id"] == self._selected_id), None)
        if cat is None:
            await interaction.response.send_message("Category not found.", ephemeral=True)
            return
        self._build_position_select(cat)

    def _build_position_select(self, cat: dict) -> None:
        """Position selection dropdown."""
        self.clear_items()
        select = discord.ui.Select(
            placeholder=f"New position for **{cat['name']}**",
            min_values=1,
            max_values=1,
        )
        for i in range(len(self.categories)):
            select.add_option(label=f"Position {i}", value=str(i))
        select.callback = self._on_position_selected
        self.add_item(select)

    async def _on_position_selected(self, interaction: discord.Interaction) -> None:
        new_pos = int(self.children[0].values[0])
        result = reorder_category(self._selected_id, new_pos)
        if result:
            await interaction.response.send_message(
                f"✅ `{result['id']}` moved to position {new_pos}.", ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Failed to reorder.", ephemeral=True)
        self._selected_id = None
        self._build_first_select()
        await interaction.edit_original_response(
            content="Category reordered. Select another to continue:",
            view=self,
        )


# ---------------------------------------------------------------------------
# Cog registration
# ---------------------------------------------------------------------------

async def setup(bot: commands.Bot) -> None:
    """Required signature for bot.add_cog()."""
    await bot.add_cog(TicketConfigCog(bot))
