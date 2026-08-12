"""Ticket workflow cog — open, manage, and close tickets."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ZERO.src.utils.storage import (
    add_ticket,
    get_categories,
    get_enabled_categories,
    get_settings,
    save_tickets,
)


def _is_staff(interaction: discord.Interaction) -> bool:
    """Check if user is staff (configured role or admin)."""
    settings = get_settings()
    admin_ids = set(settings.get("admin_role_ids", []))
    staff_ids = set(settings.get("staff_role_ids", []))

    user_roles = {r.id for r in interaction.user.roles}

    if admin_ids and user_roles & admin_ids:
        return True
    if staff_ids and user_roles & staff_ids:
        return True
    return False


# ---------------------------------------------------------------------------
# Open ticket
# ---------------------------------------------------------------------------

class TicketCog(commands.Cog, name="Tickets"):
    """Open, manage, and close support tickets."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="open-ticket",
                          description="Open a new ticket")
    async def open_ticket(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Open a ticket — picks a category from a dropdown."""
        await interaction.response.defer(ephemeral=True)

        categories = get_enabled_categories()
        if not categories:
            await interaction.followup.send(
                "❌ No ticket categories are currently enabled. Contact an admin.",
                ephemeral=True,
            )
            return

        settings = get_settings()
        active_cat_id = settings.get("active_category_id")

        if not active_cat_id:
            await interaction.followup.send(
                "❌ Ticket panel channel/category not configured. "
                "An admin needs to set it up with `/ticket-config settings set-active-category`.",
                ephemeral=True,
            )
            return

        # Build dropdown
        options = [
            discord.SelectOption(
                label=f"{c['name']}",
                value=c["id"],
                description=c.get("description", ""),
            )
            for c in categories
        ]
        select = discord.ui.Select(
            placeholder="Choose a ticket category",
            options=options,
            min_values=1,
            max_values=1,
        )
        view = discord.ui.View(timeout=120)
        view.add_item(select)

        msg = await interaction.followup.send(
            "## Open a Ticket\nSelect the category for your ticket:",
            view=view,
            ephemeral=True,
        )

        # Callback: create ticket
        async def callback(interaction2: discord.Interaction):
            category_id = select.values[0]
            category = next((c for c in categories if c["id"] == category_id), None)
            if category is None:
                await interaction2.response.send_message(
                    "❌ Category not found.", ephemeral=True
                )
                return

            # Create channel in active category
            try:
                active_cat = interaction2.guild.get_channel(active_cat_id)
                if active_cat is None or not isinstance(active_cat, discord.CategoryChannel):
                    await interaction2.response.send_message(
                        "❌ Active ticket category not found. Contact an admin.",
                        ephemeral=True,
                    )
                    return

                channel_name = f"ticket-{category_id}-{interaction2.user.name.lower().replace(' ', '-')}"
                # Avoid name collisions
                existing = [
                    ch for ch in active_cat.channels
                    if ch.name.startswith(f"ticket-{category_id}-")
                ]
                if existing:
                    channel_name = f"ticket-{category_id}-{interaction2.user.name.lower().replace(' ', '-')}-{interaction2.user.id}"

                ticket_channel = await active_cat.create_text_channel(
                    name=channel_name,
                    topic=f"Ticket: {category['name']} ({category['id']}) — opened by {interaction2.user}",
                    permission_overwrites=[
                        discord.PermissionOverwrite(
                            interaction2.guild.default_role,
                            read_messages=False,
                        ),
                        discord.PermissionOverwrite(
                            interaction2.user,
                            read_messages=True,
                            send_messages=True,
                        ),
                    ],
                )

                # Add staff to ticket
                staff_role_ids = settings.get("staff_role_ids", [])
                admin_role_ids = settings.get("admin_role_ids", [])
                for role_id in staff_role_ids + admin_role_ids:
                    role = interaction2.guild.get_role(role_id)
                    if role:
                        await ticket_channel.edit(
                            overwrites={
                                **ticket_channel.overwrites,
                                role: discord.PermissionOverwrite(
                                    read_messages=True,
                                    send_messages=True,
                                ),
                            }
                        )

                # Log ticket
                ticket = {
                    "id": ticket_channel.id,
                    "category_id": category_id,
                    "category_name": category["name"],
                    "requester_id": interaction2.user.id,
                    "requester_name": interaction2.user.name,
                    "requester_discriminator": interaction2.user.discriminator,
                    "channel_id": ticket_channel.id,
                    "opened_at": discord.utils.snowflake_time(interaction2.user.id).isoformat(),
                    "closed": False,
                    "closed_at": None,
                    "closed_by": None,
                    "messages": 0,
                }
                add_ticket(ticket)

                # Send welcome message
                welcome = (
                    f"👋 **Ticket opened!**\n"
                    f"**Category:** {category['name']}\n"
                    f"**Requester:** {interaction2.user.mention}\n\n"
                    f"Describe your issue below. A staff member will respond shortly.\n\n"
                    f"{discord.utils.format_dt(discord.utils.snowflake_time(interaction2.user.id), style='R')} ago"
                )
                await ticket_channel.send(welcome)

                # Mention staff
                staff_mentions = " ".join(
                    f"<@&{rid}>" for rid in staff_role_ids + admin_role_ids
                    if rid
                )
                if staff_mentions:
                    await ticket_channel.send(
                        f"📢 {staff_mentions} — a new ticket has been opened."
                    )

                # Update original defer message
                await interaction2.response.edit_message(
                    content=f"✅ Ticket opened in <#{ticket_channel.id}>!",
                    view=None,
                )

            except discord.Forbidden:
                await interaction2.response.send_message(
                    "❌ I don't have permission to create channels in that category.",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction2.response.send_message(
                    f"❌ Failed to open ticket: {e}",
                    ephemeral=True,
                )

        select.callback = callback

    # --- Close ticket ---------------------------------------------------------

    @app_commands.command(name="close-ticket",
                          description="Close the ticket in this channel")
    @app_commands.check(_is_staff)
    async def close_ticket(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Close the ticket in the current channel."""
        settings = get_settings()
        closed_cat_id = settings.get("closed_category_id")

        if not closed_cat_id:
            await interaction.response.send_message(
                "❌ Closed ticket category not configured. "
                "An admin needs to set it up with `/ticket-config settings set-closed-category`.",
                ephemeral=True,
            )
            return

        # Verify this is a ticket channel
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ This is not a ticket channel.", ephemeral=True
            )
            return

        # Find ticket in storage
        tickets = get_tickets()
        ticket = next((t for t in tickets if t.get("channel_id") == channel.id), None)
        if ticket is None:
            await interaction.response.send_message(
                "❌ No ticket found for this channel.", ephemeral=True
            )
            return

        # Move to closed category
        closed_cat = interaction.guild.get_channel(closed_cat_id)
        if closed_cat is None or not isinstance(closed_cat, discord.CategoryChannel):
            await interaction.response.send_message(
                "❌ Closed ticket category not found. Contact an admin.",
                ephemeral=True,
            )
            return

        try:
            old_name = channel.name
            new_name = f"closed-{channel.name}"
            ticket_channel = await channel.edit(
                category=closed_cat,
                name=new_name,
                topic=f"Closed: {ticket.get('category_name', 'Unknown')} — opened by {ticket.get('requester_name')}",
            )

            # Update ticket record
            ticket["closed"] = True
            ticket["closed_at"] = discord.utils.snowflake_time(
                int(discord.utils.utcnow().timestamp() * 1000 + 1420070400000)
            ).isoformat() if hasattr(discord.utils, 'snowflake_time') else None

            # Simpler: just use a timestamp string
            import datetime
            ticket["closed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            ticket["closed_by"] = interaction.user.id

            # Save
            save_tickets(tickets)

            # Notify
            await ticket_channel.send(
                f"🔒 **Ticket closed** by {interaction.user.mention}.\n"
                f"Category: {ticket.get('category_name')}\n"
                f"Requester: {ticket.get('requester_name')}"
            )

            await interaction.response.send_message(
                f"✅ Ticket closed and moved to closed category.",
                ephemeral=True,
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to move this channel.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to close ticket: {e}",
                ephemeral=True,
            )

    # --- Ticket panel (button to open tickets) ------------------------------

    @app_commands.command(name="ticket-panel",
                          description="Show the ticket panel interface")
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Show the ticket panel — a button to open tickets."""
        settings = get_settings()
        panel_channel_id = settings.get("panel_channel_id")

        # Check if we're in the panel channel
        if panel_channel_id and interaction.channel.id != panel_channel_id:
            # Not in panel channel — show available categories
            categories = get_enabled_categories()
            if not categories:
                await interaction.response.send_message(
                    "❌ No ticket categories enabled.", ephemeral=True
                )
                return

            options = [
                discord.SelectOption(
                    label=f"{c['name']}",
                    value=c["id"],
                    description=c.get("description", ""),
                )
                for c in categories
            ]
            select = discord.ui.Select(
                placeholder="Choose a ticket category",
                options=options,
                min_values=1,
                max_values=1,
            )
            view = discord.ui.View(timeout=120)
            view.add_item(select)

            msg = await interaction.response.send_message(
                "## Open a Ticket\nSelect a category:",
                view=view,
                ephemeral=True,
            )

            async def callback(interaction2: discord.Interaction):
                category_id = select.values[0]
                # Reuse open_ticket logic — simplified inline
                await interaction2.response.send_message(
                    f"📋 Opening ticket for **{next((c['name'] for c in categories if c['id'] == category_id), category_id)}**...",
                    ephemeral=True,
                )
                # This would need the full open flow — redirect to /open-ticket
                # For now, just tell user to use /open-ticket
                await interaction2.followup.send(
                    "Use `/open-ticket` in any channel to start the ticket flow with the dropdown.",
                    ephemeral=True,
                )

            select.callback = callback
            return

        # In panel channel — show button
        button = discord.ui.Button(
            label="🎫 Open a Ticket",
            style=discord.ButtonStyle.primary,
            emoji="📩",
        )

        view = discord.ui.View(timeout=None)
        view.add_item(button)

        await interaction.response.send_message(
            "## 🎫 Ticket Panel\nClick the button below to open a ticket.",
            view=view,
            ephemeral=False,
        )

        async def button_callback(interaction2: discord.Interaction):
            # Forward to open_ticket
            await interaction2.response.send_message(
                "Redirecting to ticket open flow...",
                ephemeral=True,
            )
            # We can't call open_ticket directly — instead, show the dropdown
            categories = get_enabled_categories()
            if not categories:
                await interaction2.followup.send(
                    "❌ No categories enabled.", ephemeral=True
                )
                return
            options = [
                discord.SelectOption(
                    label=c['name'],
                    value=c['id'],
                    description=c.get('description', ''),
                )
                for c in categories
            ]
            select = discord.ui.Select(
                placeholder="Choose a category",
                options=options,
                min_values=1,
                max_values=1,
            )
            v = discord.ui.View(timeout=120)
            v.add_item(select)

            await interaction2.response.edit_message(
                content="**Select a ticket category:**",
                view=v,
            )

            async def callback(ic: discord.Interaction):
                cid = select.values[0]
                cat = next((c for c in categories if c['id'] == cid), None)
                if cat:
                    await ic.response.send_message(
                        f"✅ Selected: **{cat['name']}** — use `/open-ticket` to create it.",
                        ephemeral=True,
                    )
                else:
                    await ic.response.send_message(
                        "❌ Category not found.", ephemeral=True
                    )

            select.callback = callback

        button.callback = button_callback


# ---------------------------------------------------------------------------
# Cog registration
# ---------------------------------------------------------------------------

async def setup(bot: commands.Bot) -> None:
    """Required signature for bot.add_cog()."""
    await bot.add_cog(TicketCog(bot))
