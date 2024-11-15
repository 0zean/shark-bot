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
        self.client = client 
        
    @app_commands.command(name="name", description="Changes username to randomized one.")
    async def name(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server!")
            return
        
        try:
            nickname = f"{choice(names)} from {choice(towns)}"
            await interaction.user.edit(nick=nickname)
            await interaction.followup.send(f"Changed your nickname to: `{nickname}`")
        except Exception as e:
            await interaction.followup.send(f"Couldn't change your name! 😭 {e}")
            return