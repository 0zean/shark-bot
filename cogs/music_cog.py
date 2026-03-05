import asyncio
import logging

import discord
from discord import app_commands
from discord.channel import CategoryChannel, ForumChannel
from discord.ext import commands, tasks

from schemas.track import Track
from services.music_service import MusicService
from utils.config_interface import ConfigInterface
from utils.helper import convert_time

logger = logging.getLogger(__name__)


class MusicBot(commands.Cog):
    """Cog that exposes music playback commands to Discord.

    All business logic is delegated to :class:`services.music_service.MusicService`.
    """

    def __init__(self, client: commands.Bot, config: ConfigInterface, music_service: MusicService) -> None:
        self.client: commands.Bot = client
        self.config: ConfigInterface = config
        self.music_service: MusicService = music_service
        self.last_channel: dict[int | None, discord.interactions.InteractionChannel | None] = {}
        self.check_inactivity.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _validate_interaction_context(self, interaction: discord.Interaction) -> bool:
        """Verify the interaction is guild-scoped and the user is in a voice channel.

        Args:
            interaction: The incoming Discord interaction.

        Returns:
            ``True`` if the context is valid, ``False`` otherwise (followup sent).
        """
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

    def _create_embed(self, interaction: discord.Interaction, track: Track, status: str) -> discord.Embed:
        """Build an embed for a track status message.

        Args:
            interaction: The Discord interaction (used for user colour).
            track: The track to display.
            status: The status string shown as the embed title.

        Returns:
            A formatted :class:`discord.Embed`.
        """
        embed = discord.Embed(
            title=status,
            description=f"**{track.title}** - `{convert_time(track.duration)}`",
            color=interaction.user.color,
        )
        if track.thumbnail_url:
            embed.set_thumbnail(url=track.thumbnail_url)
        return embed

    async def cog_unload(self) -> None:
        """Cancel background tasks on cog unload."""
        self.check_inactivity.cancel()

    # ------------------------------------------------------------------
    # Background task – inactivity check
    # ------------------------------------------------------------------

    @tasks.loop(seconds=60)
    async def check_inactivity(self) -> None:
        """Disconnect from guilds that have been inactive for the configured period."""
        inactive_guilds = self.music_service.get_inactive_guilds()
        for guild_id in inactive_guilds:
            guild = self.client.get_guild(guild_id)
            if guild and guild.voice_client:
                await guild.voice_client.disconnect(force=True)
                self.music_service.clear_queue(guild_id)
                self.music_service.clear_activity(guild_id)
                self.music_service.clear_song_length(guild_id)
                logger.info("Disconnected from %s due to inactivity", guild.name, extra={"guild_id": guild_id})

    @check_inactivity.before_loop
    async def before_check_inactivity(self) -> None:
        """Wait until the bot is ready before the inactivity loop starts."""
        await self.client.wait_until_ready()

    # ------------------------------------------------------------------
    # Slash commands
    # ------------------------------------------------------------------

    @app_commands.command(name="play", description="Play a song from YouTube, SoundCloud, or upload an audio file")
    async def play(
        self, interaction: discord.Interaction, search: str | None = None, file: discord.Attachment | None = None
    ) -> None:
        """Queue and play a track.

        Args:
            interaction: The Discord interaction.
            search: A YouTube/SoundCloud search query or URL.
            file: An optional audio attachment to play directly.
        """
        await interaction.response.defer()

        if not await self._validate_interaction_context(interaction):
            return

        if file:
            is_valid, error_msg = self.music_service.validate_file(file.filename, file.size)
            if not is_valid:
                await interaction.followup.send(error_msg or "Invalid file.")
                return

        if interaction.guild_id:
            self.music_service.update_activity(interaction.guild_id)
            self.last_channel[interaction.guild_id] = interaction.channel

        voice_channel = interaction.user.voice.channel  # type: ignore[union-attr]
        assert voice_channel is not None  # guaranteed by _validate_interaction_context
        try:
            voice_client = interaction.guild.voice_client  # type: ignore[union-attr]
            if not voice_client:
                voice_client = await voice_channel.connect()
        except discord.errors.ClientException as e:
            logger.error("Error connecting to voice channel", exc_info=e)
            await interaction.followup.send("Error connecting to voice channel. Please try again.")
            return

        track, error_msg = await self.music_service.extract_track_info(
            search=search,
            file_url=file.url if file else None,
            file_name=file.filename if file else None,
        )

        if not track:
            await interaction.followup.send(error_msg or "Unknown error extracting track")
            return

        if isinstance(voice_client, discord.VoiceClient) and not voice_client.is_playing():
            status = "Now Playing 🎶"
        else:
            status = "Added to Queue 📝"

        if isinstance(interaction.guild_id, int):
            self.music_service.add_to_queue(interaction.guild_id, track)

        embed = self._create_embed(interaction, track, status)
        await interaction.followup.send(embed=embed)

        # Play immediately if nothing is currently playing
        if isinstance(voice_client, discord.VoiceClient) and not voice_client.is_playing():
            await self.play_next(interaction, send_message=False)

        # Extend the inactivity grace period by this song's duration
        if isinstance(interaction.guild_id, int) and track.duration is not None:
            self.music_service.add_song_length(interaction.guild_id, track.duration)

    async def play_next(
        self,
        interaction: discord.Interaction,
        send_message: bool = True,
        _retries: int = 0,
    ) -> None:
        """Advance to the next track in the queue.

        Args:
            interaction: The Discord interaction that initiated playback.
            send_message: Whether to post a "Now Playing" embed. Defaults to ``True``.
            _retries: Internal retry counter — prevents infinite recursion on
                persistent playback errors. Max 3 retries before giving up.
        """
        _MAX_RETRIES = 3

        if not interaction.guild or not isinstance(interaction.guild_id, int):
            return

        self.music_service.update_activity(interaction.guild_id)

        guild_queue = self.music_service.get_queue(interaction.guild_id)
        if not guild_queue:
            if interaction.channel and not isinstance(interaction.channel, (ForumChannel, CategoryChannel)):
                await interaction.channel.send("Queue is empty! 🕳️")
            return

        voice_client = interaction.guild.voice_client
        if not voice_client:
            return

        track = guild_queue.pop(0)
        self.music_service.update_activity(interaction.guild_id)

        ffmpeg_opts = self.music_service.get_ffmpeg_options(track)

        try:
            source = await discord.FFmpegOpusAudio.from_probe(track.url, **ffmpeg_opts)  # type: ignore[arg-type]

            def after_playing(error: str | Exception | None) -> None:
                if error:
                    logger.error(
                        "Error in playback",
                        exc_info=error if isinstance(error, Exception) else Exception(error),
                    )
                asyncio.run_coroutine_threadsafe(
                    self.play_next(interaction, send_message=True),
                    self.client.loop,
                )

            if isinstance(voice_client, discord.VoiceClient):
                voice_client.play(source, after=after_playing)

            if send_message and interaction.channel and not isinstance(
                interaction.channel, (ForumChannel, CategoryChannel)
            ):
                embed = self._create_embed(interaction, track, status="Now Playing 🎶")
                await interaction.channel.send(embed=embed)

        except Exception as e:
            logger.exception("Error playing %s", track.title)
            if interaction.channel and not isinstance(interaction.channel, (ForumChannel, CategoryChannel)):
                await interaction.channel.send(f"Error playing {track.title}: {e}")

            if _retries < _MAX_RETRIES:
                logger.warning("Retrying next track (attempt %d/%d)", _retries + 1, _MAX_RETRIES)
                await self.play_next(interaction, send_message=True, _retries=_retries + 1)
            else:
                logger.error("Max retries reached — stopping playback.")

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction) -> None:
        """Skip the currently playing track.

        Args:
            interaction: The Discord interaction.
        """
        if not interaction.guild or not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server!")
            return

        self.music_service.update_activity(interaction.guild_id)
        self.last_channel[interaction.guild_id] = interaction.channel

        voice_client = interaction.guild.voice_client
        if isinstance(voice_client, discord.VoiceClient) and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped!")
        else:
            await interaction.response.send_message("Nothing is playing!")

    @app_commands.command(name="leave", description="Disconnect the bot from voice channel")
    async def leave(self, interaction: discord.Interaction) -> None:
        """Disconnect the bot from the current voice channel and clear the queue.

        Args:
            interaction: The Discord interaction.
        """
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server!")
            return

        self.last_channel[interaction.guild_id] = interaction.channel

        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.disconnect(force=True)
            if interaction.guild_id is not None:
                self.music_service.clear_queue(interaction.guild_id)
            await interaction.response.send_message("👋 Disconnected from voice channel!")
        else:
            await interaction.response.send_message("I'm not in a voice channel!")

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        """Disconnect when the bot is left alone in a voice channel.

        Args:
            member: The guild member whose voice state changed.
            before: The member's voice state before the change.
            after: The member's voice state after the change.
        """
        if member.guild.voice_client is None:
            return

        # Refresh activity when a user joins the bot's channel
        if after.channel and after.channel.id == member.guild.voice_client.channel.id:  # type: ignore[union-attr,attr-defined]
            self.music_service.update_activity(member.guild.id)

        # Fire-and-forget: check if bot is alone after a short grace period
        voice_client = member.guild.voice_client
        if (
            isinstance(voice_client, discord.VoiceClient)
            and voice_client.is_connected()
            and len(voice_client.channel.members) <= 1  # type: ignore[union-attr]
        ):
            asyncio.create_task(self._handle_alone_in_channel(member.guild, voice_client))

    async def _handle_alone_in_channel(
        self, guild: discord.Guild, voice_client: discord.VoiceClient
    ) -> None:
        """Disconnect and notify after a 5-second grace period if still alone.

        Args:
            guild: The guild the bot is connected to.
            voice_client: The active voice client for the guild.
        """
        await asyncio.sleep(5)

        # Re-check after the grace period — a user may have rejoined
        if not voice_client.is_connected() or len(voice_client.channel.members) > 1:  # type: ignore[union-attr]  # discord.py stubs gap
            return

        logger.info(
            "Disconnecting from %s — bot was left alone", guild.name, extra={"guild_id": guild.id}
        )

        last_text_channel = self.last_channel.get(guild.id)
        if last_text_channel and not isinstance(last_text_channel, (ForumChannel, CategoryChannel)):
            try:
                await last_text_channel.send("Disconnecting because I was left alone in the voice channel! 👋")
            except discord.HTTPException:
                pass  # Non-fatal — continue with disconnection

        await voice_client.disconnect(force=True)
        self.music_service.clear_queue(guild.id)
        self.music_service.clear_activity(guild.id)
        self.music_service.clear_song_length(guild.id)
