import asyncio
from datetime import datetime

import discord
from discord import app_commands
from discord.channel import CategoryChannel, ForumChannel
from discord.ext import commands, tasks

from extractors.extractor_factory import get_extractor
from schemas.track import Track
from utils.config_interface import ConfigInterface
from utils.helper import convert_time, get_audio_duration

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


class MusicBot(commands.Cog):
    def __init__(self, client: commands.Bot, config: ConfigInterface):
        self.client: commands.Bot = client
        self.config: ConfigInterface = config
        self.queue: dict[int, list[Track]] = {}  # Dictionary to store queues for different guilds
        self.last_activity: dict[int, datetime] = {}  # Dictionary to store last activity time for each guild
        self.last_channel: dict[
            int | None, discord.interactions.InteractionChannel | None
        ] = {}  # Dictionary to store last channel bot was used in
        self.check_inactivity.start()
        self.song_length: int = 0

    async def _validate_interaction_context(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server!")
            return False
        if (
            not isinstance(interaction.user, discord.Member)
            or not interaction.user.voice
            or not interaction.user.voice.channel
        ):
            await interaction.followup.send("You need to be in a voice channel!")
            return False
        return True

    async def _validate_file(self, file: discord.Attachment | None, interaction: discord.Interaction) -> bool:
        if file:
            if not file.filename.lower().endswith(self.config.AUDIO_TYPES):
                await interaction.followup.send(
                    f"Invalid file type! supported formats: `{', '.join(self.config.AUDIO_TYPES)}`"
                )
                return False
            if file.size > self.config.MAX_FILE_SIZE:
                await interaction.followup.send(f"File greater than 10MB!: `{(file.size / 1000000):.2f}`")
                return False
            return True
        return False

    async def _extract_track_info(
        self, interaction: discord.Interaction, search: str | None, file: discord.Attachment | None
    ) -> Track | None:
        if file:
            duration = await get_audio_duration(file.url)
            return Track(url=file.url, title=file.filename, thumbnail_url=None, duration=duration)

        if not search:
            await interaction.followup.send("You need to provide a search query or a file!")
            return None

        try:
            extractor = get_extractor(search=search)
            return await extractor.extract(search=search, config=self.config)
        except Exception as e:
            await interaction.followup.send(f"An error occurred in in `/play` command: {e}")
            return None

    def _add_to_queue(self, guild_id: int, track: Track) -> None:
        if guild_id not in self.queue:
            self.queue[guild_id] = []
        self.queue[guild_id].append(track)

    def _create_embed(self, interaction: discord.Interaction, track: Track, status: str) -> discord.Embed:
        embed = discord.Embed(
            title=status,
            description=f"**{track.title}** - `{convert_time(track.duration)}`",
            color=interaction.user.color,
        )
        if track.thumbnail_url:
            embed.set_thumbnail(url=track.thumbnail_url)
        return embed

    async def cog_unload(self) -> None:
        self.check_inactivity.cancel()

    @tasks.loop(seconds=60)
    async def check_inactivity(self) -> None:
        """Check if bot has been inactive for 10 mins."""
        current_time = datetime.now()
        for guild in self.client.guilds:
            voice_client = guild.voice_client
            if voice_client is None:
                continue

            # Check for inactivity
            last_active = self.last_activity.get(guild.id)
            if last_active:
                inactive_time = (current_time - last_active).total_seconds()
                if inactive_time > self.config.INACTIVITY_TIMER + self.song_length:
                    await voice_client.disconnect(force=True)
                    if guild.id in self.queue:
                        self.queue[guild.id].clear()
                    self.last_activity.pop(guild.id, None)
                    print(f"Disconnected from {guild.name} due to inactivity")

    @check_inactivity.before_loop
    async def before_check_inactivity(self) -> None:
        """Check if client is ready before calculating inactivity."""
        await self.client.wait_until_ready()

    def update_activity(self, guild_id: int) -> None:
        """
        Update activity timestamp for various actions.

        Args:
            guild_id (int): id of the guild function is called from.
        """
        self.last_activity[guild_id] = datetime.now()

    def get_queue(self, guild_id: int) -> list[Track]:
        """Get the queue for a specific guild"""
        if guild_id not in self.queue:
            self.queue[guild_id] = []
        return self.queue[guild_id]

    @app_commands.command(name="play", description="Play a song from YouTube, SoundCloud, or upload an audio file")
    async def play(
        self, interaction: discord.Interaction, search: str | None = None, file: discord.Attachment | None = None
    ) -> None:
        await interaction.response.defer()

        if not await self._validate_interaction_context(interaction):
            return

        if file and not await self._validate_file(file, interaction):
            return

        # Update activity timestamp when play command is used
        if interaction.guild_id:
            self.update_activity(interaction.guild_id)
            self.last_channel[interaction.guild_id] = interaction.channel

        # Connect to voice channel if not already connected
        voice_channel = interaction.user.voice.channel
        try:
            voice_client = interaction.guild.voice_client
            if not voice_client:
                voice_client = await voice_channel.connect()
        except discord.errors.ClientException:
            await interaction.followup.send("Error connecting to voice channel. Please try again.")
            return

        track = await self._extract_track_info(interaction, search, file)
        if not track:
            return

        if isinstance(voice_client, discord.VoiceClient) and not voice_client.is_playing():
            status = "Now Playing 🎶"
        else:
            status = "Added to Queue 📝"

        if isinstance(interaction.guild_id, int):
            self._add_to_queue(interaction.guild_id, track)

        embed = self._create_embed(interaction, track, status)
        await interaction.followup.send(embed=embed)

        # TODO: Add default thumbnail file for attachments
        # if file or is_discord_url:
        #     thumbnail_file = discord.File("/root/dev/discord-bot/assets/music_file.png", filename="music_file.png")
        #     embed.set_image(url="attachment://music_file.png")
        #     await interaction.followup.send(file=thumbnail_file, embed=embed)
        # else:

        # Play if not already playing
        if isinstance(voice_client, discord.VoiceClient) and not voice_client.is_playing():
            await self.play_next(interaction, send_message=False)

        # Add song time to timeout length
        if track.duration is not None:
            self.song_length += track.duration

    async def play_next(self, interaction: discord.Interaction, send_message: bool = True) -> None:
        """
        Method called by `play` command to initialize music play.

        Args:
            interaction (discord.Interaction): A Discord interaction.
            send_message (bool, optional): Whether to send embedded message or not. Defaults to True.
        """
        if not interaction.guild or not type(interaction.guild_id) == int:
            return

        self.update_activity(interaction.guild_id)

        guild_queue = self.get_queue(interaction.guild_id)
        if (
            not guild_queue
            and interaction.channel
            and not isinstance(interaction.channel, (ForumChannel, CategoryChannel))
        ):
            await interaction.channel.send("Queue is empty! 🕳️")
            return

        voice_client = interaction.guild.voice_client
        if not voice_client:
            return

        track = guild_queue.pop(0)
        self.update_activity(interaction.guild_id)  # Update activity timestamp

        # Choose FFMPEG options based on source type
        if isinstance(track.url, discord.Attachment) or "cdn.discordapp.com" in track.url:
            # Use high quality settings for Discord uploads and CDN
            ffmpeg_opts = self.config.LOCAL_FFMPEG_OPTIONS
        else:
            # Use bandwidth-optimized settings for YouTube/Soundcloud streams
            ffmpeg_opts = self.config.STREAM_FFMPEG_OPTIONS

        try:
            source = await discord.FFmpegOpusAudio.from_probe(track.url, **ffmpeg_opts)  # type: ignore

            def after_playing(error: str):
                if error:
                    print(f"Error in playback: {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(interaction, send_message=True), self.client.loop)

            voice_client.play(source, after=after_playing)  # type: ignore

            if (
                send_message
                and interaction.channel
                and not isinstance(interaction.channel, (ForumChannel, CategoryChannel))
            ):
                embed = self._create_embed(interaction, track, status="Now Playing 🎶")
                await interaction.channel.send(embed=embed)

        except Exception as e:
            if interaction.channel and not isinstance(interaction.channel, (ForumChannel, CategoryChannel)):
                await interaction.channel.send(f"Error playing {track.title}: {e}")
            await self.play_next(interaction)

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction) -> None:
        """
        Command to skip current song or stop if no queue.

        Args:
            interaction (discord.Interaction): A Discord interaction.
        """
        if not interaction.guild or not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server!")
            return

        # Update activity timestamp when skip command is used
        self.update_activity(interaction.guild_id)
        self.last_channel[interaction.guild_id] = interaction.channel

        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():  # type: ignore
            voice_client.stop()  # type: ignore
            await interaction.response.send_message("⏭️ Skipped!")
        else:
            await interaction.response.send_message("Nothing is playing!")

    @app_commands.command(name="leave", description="Disconnect the bot from voice channel")
    async def leave(self, interaction: discord.Interaction) -> None:
        """
        Command to disconnect bot from a voice channel if in one.

        Args:
            interaction (discord.Interaction): A Discord interaction.
        """
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!")
            return

        self.last_channel[interaction.guild_id] = interaction.channel

        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.disconnect(force=True)
            if interaction.guild_id in self.queue:
                self.queue[interaction.guild_id].clear()
            await interaction.response.send_message("👋 Disconnected from voice channel!")
        else:
            await interaction.response.send_message("I'm not in a voice channel!")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        """
        Event listener for voice state updates.

        Args:
            member (discord.Member): A Discord member to a Guild.
            before (discord.VoiceState): A Discord user's voice state before.
            after (discord.VoiceState):  A Discord user's voice state after.
        """
        if member.guild.voice_client is None:
            return

        # Update activity when someone joins or moves in the voice channel
        if after.channel and after.channel.id == member.guild.voice_client.channel.id:  # type: ignore
            self.update_activity(member.guild.id)

        # Check if the bot is alone in the voice channel
        voice_client = member.guild.voice_client
        if voice_client and voice_client.is_connected() and len(voice_client.channel.members) <= 1:  # type: ignore
            await asyncio.sleep(5)  # Wait 5 seconds before checking again

            # Check again after delay to make sure bot is still alone
            if voice_client.is_connected() and len(voice_client.channel.members) <= 1:  # type: ignore
                print(f"Disconnected from {member.guild.name} - bot was left alone")

                # Try to send message to the last channel where a command was used
                try:
                    # Get the last interaction's channel
                    last_text_channel = self.last_channel.get(member.guild.id)

                    if last_text_channel and not isinstance(last_text_channel, (ForumChannel, CategoryChannel)):
                        await last_text_channel.send("Disconnecting because I was left alone in the voice channel! 👋")
                except discord.HTTPException:
                    # If sending message fails, just continue with disconnection
                    pass

                # Perform cleanup
                await voice_client.disconnect(force=True)
                if member.guild.id in self.queue:
                    self.queue[member.guild.id].clear()
                self.last_activity.pop(member.guild.id, None)
