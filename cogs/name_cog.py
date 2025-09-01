import asyncio
from pathlib import Path
from random import choice

import discord
from discord import app_commands
from discord.ext import commands

from utils.config_interface import ConfigInterface

names = [name.strip() for name in Path("firstnames.txt").read_text("utf-8").splitlines()]
towns = [town.strip() for town in Path("towns.txt").read_text("utf-8").splitlines()]

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


class NameChanger(commands.Cog):
    def __init__(self, client: commands.Bot, config: ConfigInterface):
        self.client: commands.Bot = client
        self.config: ConfigInterface = config

    @app_commands.command(name="name", description="Changes username to randomized one.")
    async def name(self, interaction: discord.Interaction) -> None:
        """
        Command to change user's name to a randomized one.

        Args:
            interaction (discord.Interaction): A Discrod interaction.
        """
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server!")
            return

        try:
            nickname = f"{choice(names)} from {choice(towns)}"

            member = interaction.guild.get_member(interaction.user.id)
            if member:
                await member.edit(nick=nickname)
                await interaction.followup.send(f"Changed your nickname to: `{nickname}`")

        except discord.HTTPException as e:
            await interaction.followup.send(f"Couldn't change your name! 😭 `{e}`")
            return

    @app_commands.command(name="clean", description="Remove bot messages from the channel (default: 100)")
    async def clean(self, interaction: discord.Interaction, limit: int = 100) -> None:
        """
        Command to remove bot messages from a channel.

        Args:
            interaction (discord.Interaction): A Discord interaction.
            limit (int, optional): Number of messages to delete. Defaults to 100.
        """
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server!")
            return

        try:
            if isinstance(interaction.channel, discord.TextChannel):
                deleted = await interaction.channel.purge(limit=limit + 1, check=lambda m: m.author == self.client.user)
                confirm = await interaction.channel.send(f"Deleted `{len(deleted) - 1}` messages! 🧹")
                await asyncio.sleep(self.config.DELETE_TIMER)
                await confirm.delete()
            else:
                await interaction.followup.send("This command can only be used in text channels!")
                return

        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to delete messages!")
        except discord.HTTPException as e:
            await interaction.followup.send(f"An error occurred while deleting messages: {str(e)}")
