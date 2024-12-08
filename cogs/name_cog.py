import asyncio
from random import choice

import discord
from discord import app_commands
from discord.ext import commands

names = [name.strip() for name in open("firstnames.txt", "r")]
towns = [town.strip() for town in open("towns.txt", "r")]

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


class NameChanger(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

    @app_commands.command(
        name="name", description="Changes username to randomized one."
    )
    async def name(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send(
                "This command can only be used in a server!"
            )
            return

        try:
            nickname = f"{choice(names)} from {choice(towns)}"
            await interaction.user.edit(nick=nickname)
            await interaction.followup.send(f"Changed your nickname to: `{nickname}`")
        except Exception as e:
            await interaction.followup.send(f"Couldn't change your name! 😭 `{e}`")
            return

    @app_commands.command(
        name="clean", description="Remove bot messages from the channel (default: 100)"
    )
    async def clean(self, interaction: discord.Interaction, limit: int = 100):
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send(
                "This command can only be used in a server!"
            )
            return

        # self.last_channel[interaction.guild_id] = interaction.channel

        try:
            # Delete messages
            deleted = await interaction.channel.purge(
                limit=limit + 1, check=lambda m: m.author == self.client.user
            )

            # Send confirmation message that will delete itself after 5 seconds
            confirm = await interaction.channel.send(
                f"Deleted `{len(deleted) - 1}` messages! 🧹"
            )
            await asyncio.sleep(5)
            await confirm.delete()
        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have permission to delete messages!"
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"An error occurred while deleting messages: {str(e)}"
            )
