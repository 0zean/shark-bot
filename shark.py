import asyncio
import os
from datetime import datetime
from typing import Optional

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands, tasks
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
        self.last_activity = {}  # Dictionary to store last activity time for each guild
        self.last_channel = {}
        self.check_inactivity.start()

    def cog_unload(self):
        self.check_inactivity.cancel()

    @tasks.loop(seconds=30)  # Check every 30 seconds
    async def check_inactivity(self):
        current_time = datetime.now()
        for guild in self.client.guilds:
            voice_client = guild.voice_client
            if voice_client is None:
                continue

            # Check for inactivity
            last_active = self.last_activity.get(guild.id)
            if last_active:
                inactive_time = (current_time - last_active).total_seconds()
                if inactive_time > 600:
                    await voice_client.disconnect()
                    if guild.id in self.queue:
                        self.queue[guild.id].clear()
                    self.last_activity.pop(guild.id, None)
                    print(f"Disconnected from {guild.name} due to inactivity")

    @check_inactivity.before_loop
    async def before_check_inactivity(self):
        await self.client.wait_until_ready()

    # Update activity timestamp for various actions
    def update_activity(self, guild_id: int):
        self.last_activity[guild_id] = datetime.now()

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

        # Update activity timestamp when play command is used
        self.update_activity(interaction.guild_id)
        self.last_channel[interaction.guild_id] = interaction.channel

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
                # Check if the input is a SoundCloud link
                is_soundcloud = "soundcloud.com" in search

                if is_soundcloud:
                    # Extract SoundCloud info
                    info = ydl.extract_info(search, download=False)
                else:
                    # Use YouTube search
                    info = ydl.extract_info(f"ytsearch:{search}", download=False)
                    if "entries" in info:
                        info = info["entries"][0]

                url = info["url"]
                title = info["title"]
                thumbnail_url = (
                    info.get("thumbnail")
                    if is_soundcloud
                    else f"https://img.youtube.com/vi/{info['id']}/default.jpg"
                )

                if not voice_client.is_playing():
                    status = "Now Playing 🎶"
                else:
                    status = "Added to Queue 📝"

                guild_queue = self.get_queue(interaction.guild_id)
                guild_queue.append((url, title, thumbnail_url))

                embed = discord.Embed(
                    title=status,
                    description=f"**{title}**",
                    color=interaction.user.color,
                )
                embed.set_thumbnail(url=thumbnail_url)

                await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
            return

        # Play if not already playing
        if not voice_client.is_playing():
            await self.play_next(interaction, send_message=False)

    async def play_next(
        self, interaction: discord.Interaction, send_message: bool = True
    ):
        if not interaction.guild:
            return

        self.update_activity(interaction.guild_id)

        guild_queue = self.get_queue(interaction.guild_id)
        if not guild_queue:
            await interaction.channel.send("Queue is empty! 🕳️")
            return

        voice_client = interaction.guild.voice_client
        if not voice_client:
            return

        url, title, thumbnail_url = guild_queue.pop(0)
        self.update_activity(interaction.guild_id)  # Update activity timestamp

        try:
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)

            def after_playing(error):
                if error:
                    print(f"Error in playback: {error}")
                asyncio.run_coroutine_threadsafe(
                    self.play_next(interaction, send_message=True), self.client.loop
                )

            voice_client.play(source, after=after_playing)

            if send_message:
                embed = discord.Embed(
                    title="Now Playing 🎶",
                    description=f"**{title}**",
                    color=interaction.user.color,
                )
                embed.set_thumbnail(url=thumbnail_url)

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

        # Update activity timestamp when skip command is used
        self.update_activity(interaction.guild_id)
        self.last_channel[interaction.guild_id] = interaction.channel

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

        self.last_channel[interaction.guild_id] = interaction.channel

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

        self.last_channel[interaction.guild_id] = interaction.channel

        try:
            # Delete messages
            deleted = await interaction.channel.purge(
                limit=limit + 1, check=lambda m: m.author == self.client.user
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

    # Event listener for voice state updates
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.guild.voice_client is None:
            return

        # Update activity when someone joins or moves in the voice channel
        if after.channel and after.channel.id == member.guild.voice_client.channel.id:
            self.update_activity(member.guild.id)

        # Check if the bot is alone in the voice channel
        voice_client = member.guild.voice_client
        if (
            voice_client
            and voice_client.is_connected()
            and len(voice_client.channel.members) <= 1
        ):
            await asyncio.sleep(5)  # Wait 5 seconds before checking again

            # Check again after delay to make sure bot is still alone
            if voice_client.is_connected() and len(voice_client.channel.members) <= 1:
                print(f"Disconnected from {member.guild.name} - bot was left alone")

                # Try to send message to the last channel where a command was used
                try:
                    # Get the last interaction's channel
                    last_text_channel = self.last_channel.get(member.guild.id)

                    if last_text_channel:
                        await last_text_channel.send(
                            "Disconnecting because I was left alone in the voice channel! 👋"
                        )
                except discord.HTTPException:
                    # If sending message fails, just continue with disconnection
                    pass

                # Perform cleanup
                await voice_client.disconnect()
                if member.guild.id in self.queue:
                    self.queue[member.guild.id].clear()
                self.last_activity.pop(member.guild.id, None)


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
