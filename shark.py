import asyncio
import os
from typing import Optional

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Setup YDL and FFMPEG options
FFMPEG_OPTIONS = {"options": "-vn"}
YDL_OPTIONS = {
    "format": "bestaudio",
    "noplaylist": True,
    "username": "oauth",
    "password": "",
}


class MusicBot(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.queue = {}  # Dictionary to store queues for different guilds

    def get_queue(self, guild_id: int):
        """Get the queue for a specific guild"""
        if guild_id not in self.queue:
            self.queue[guild_id] = []
        return self.queue[guild_id]

    @app_commands.command(name="play", description="Play a song from YouTube")
    async def play(self, interaction: discord.Interaction, search: str):
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send(
                "This command can only be used in a server!"
            )
            return

        # Check if user is in a voice channel
        if not interaction.user.voice:
            await interaction.followup.send("You need to be in a voice channel!")
            return

        voice_channel = interaction.user.voice.channel

        # Connect to voice channel if not already connected
        try:
            voice_client = interaction.guild.voice_client
            if not voice_client:
                voice_client = await voice_channel.connect()
        except discord.errors.ClientException:
            await interaction.followup.send(
                "Error connecting to voice channel. Please try again."
            )
            return

        # Search and queue the song
        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)
                if "entries" in info:
                    info = info["entries"][0]
                url = info["url"]
                title = info["title"]
                thumbnail_id = info["id"]

                if not self.get_queue(interaction.guild_id):
                    status = "Now Playing 🎶"
                else:
                    status = "Added to Queue 📝"

                guild_queue = self.get_queue(interaction.guild_id)
                guild_queue.append((url, title, thumbnail_id))

                embed = discord.Embed(
                    title=status,
                    description=f"**{title}**",
                    color=interaction.message.author.color,
                )
                embed.set_thumbnail(
                    url=f"https://img.youtube.com/vi/{thumbnail_id}/default.jpg"
                )

                await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
            return

        # Play if not already playing
        if not voice_client.is_playing():
            await self.play_next(interaction)

    async def play_next(self, interaction: discord.Interaction):
        if not interaction.guild:
            return

        guild_queue = self.get_queue(interaction.guild_id)
        if not guild_queue:
            await interaction.channel.send("Queue is empty!")
            return

        voice_client = interaction.guild.voice_client
        if not voice_client:
            return

        url, title, thumbnail_id = guild_queue.pop(0)

        try:
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)

            def after_playing(error):
                if error:
                    print(f"Error in playback: {error}")
                asyncio.run_coroutine_threadsafe(
                    self.play_next(interaction), self.client.loop
                )

            voice_client.play(source, after=after_playing)

            if len(self.get_queue(interaction.guild_id)) > 1:
                embed = discord.Embed(
                    title="Now Playing EPIC 🎶",
                    description=f"**{title}**",
                    color=interaction.message.author.color,
                )
                embed.set_thumbnail(
                    url=f"https://img.youtube.com/vi/{thumbnail_id}/default.jpg"
                )

                await interaction.channel.send(embed=embed)

        except Exception as e:
            await interaction.channel.send(f"Error playing {title}: {str(e)}")
            await self.play_next(interaction)

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!"
            )
            return

        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped!")
        else:
            await interaction.response.send_message("Nothing is playing!")

    @app_commands.command(
        name="leave", description="Disconnect the bot from voice channel"
    )
    async def leave(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!"
            )
            return

        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.disconnect()
            if interaction.guild_id in self.queue:
                self.queue[interaction.guild_id].clear()
            await interaction.response.send_message(
                "👋 Disconnected from voice channel!"
            )
        else:
            await interaction.response.send_message("I'm not in a voice channel!")

    @app_commands.command(
        name="clean", description="Remove bot messages from the channel (default: 100)"
    )
    async def clean(self, interaction: discord.Interaction, limit: Optional[int] = 100):
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send(
                "This command can only be used in a server!"
            )
            return

        try:
            # Delete messages
            deleted = await interaction.channel.purge(
                limit=limit, check=lambda m: m.author == self.client.user
            )

            # Send confirmation message that will delete itself after 5 seconds
            confirm = await interaction.followup.send(
                f"Deleted {len(deleted)} messages! 🧹"
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


class MusicBotClient(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",  # Prefix still required but won't be used
            intents=intents,
        )

    async def setup_hook(self):
        await self.add_cog(MusicBot(self))
        await self.tree.sync()  # Sync slash commands with Discord

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("")


async def main():
    async with MusicBotClient() as client:
        await client.start(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
