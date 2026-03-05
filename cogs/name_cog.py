import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from services.name_service import NameService
from utils.config_interface import ConfigInterface

logger = logging.getLogger(__name__)


class NameChanger(commands.Cog):
    """Cog for nickname management and channel cleanup commands."""

    def __init__(self, client: commands.Bot, config: ConfigInterface, name_service: NameService) -> None:
        self.client: commands.Bot = client
        self.config: ConfigInterface = config
        self.name_service = name_service

    @app_commands.command(name="name", description="Changes username to randomized one.")
    async def name(self, interaction: discord.Interaction) -> None:
        """Change the invoking user's nickname to a randomly generated one.

        Args:
            interaction: The Discord interaction.
        """
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server!")
            return

        try:
            nickname = self.name_service.generate_random_nickname()
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                await member.edit(nick=nickname)
                logger.info(
                    "Changed nickname for user %s",
                    interaction.user.id,
                    extra={"user_id": interaction.user.id, "guild_id": interaction.guild.id},
                )
                await interaction.followup.send(f"Changed your nickname to: `{nickname}`")

        except discord.HTTPException as e:
            logger.error("Error changing nickname", exc_info=e)
            await interaction.followup.send(f"Couldn't change your name! 😭 `{e}`")

    @app_commands.command(name="clean", description="Remove bot messages from the channel (default: 100)")
    async def clean(self, interaction: discord.Interaction, limit: int = 100) -> None:
        """Delete bot-authored messages from the current text channel.

        Args:
            interaction: The Discord interaction.
            limit: Maximum number of messages to scan. Defaults to 100.
        """
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server!")
            return

        try:
            if isinstance(interaction.channel, discord.TextChannel):
                deleted = await interaction.channel.purge(limit=limit + 1, check=lambda m: m.author == self.client.user)
                confirm = await interaction.channel.send(f"Deleted `{len(deleted) - 1}` messages! 🧹")
                logger.info(
                    "Purged bot messages",
                    extra={"guild_id": interaction.guild.id, "channel_id": interaction.channel.id},
                )
                await asyncio.sleep(self.config.DELETE_TIMER)
                await confirm.delete()
            else:
                await interaction.followup.send("This command can only be used in text channels!")

        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to delete messages!")
        except discord.HTTPException as e:
            logger.error("Error deleting messages", exc_info=e)
            await interaction.followup.send(f"An error occurred while deleting messages: {e}")
