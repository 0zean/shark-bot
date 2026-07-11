import logging
import os
from datetime import datetime, timezone

from extractors.extractor_factory import get_extractor
from schemas.track import Track
from utils.config import BotConfig
from utils.helper import get_audio_duration

logger = logging.getLogger(__name__)


class MusicService:
    """Business logic layer for music playback.

    Manages per-guild queues, activity timestamps, and track extraction.
    Does not depend on Discord primitives.
    """

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.queue: dict[int, list[Track]] = {}
        self.last_activity: dict[int, datetime] = {}
        # Per-guild accumulated song duration (seconds) used to extend the
        # inactivity grace period while tracks are queued.
        self._song_length: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def get_queue(self, guild_id: int) -> list[Track]:
        """Return (and lazily initialise) the track queue for a guild.

        Args:
            guild_id (int): The Discord guild ID.

        Returns:
            list[Track]: The mutable track queue for the guild.
        """
        if guild_id not in self.queue:
            self.queue[guild_id] = []
        return self.queue[guild_id]

    def add_to_queue(self, guild_id: int, track: Track) -> None:
        """Append a track to the guild's queue.

        Args:
            guild_id (int): The Discord guild ID.
            track (Track): The track to add.
        """
        self.get_queue(guild_id).append(track)

    def clear_queue(self, guild_id: int) -> None:
        """Clear all queued tracks for a guild.

        Args:
            guild_id (int): The Discord guild ID.
        """
        if guild_id in self.queue:
            self.queue[guild_id].clear()

    # ------------------------------------------------------------------
    # Activity tracking
    # ------------------------------------------------------------------

    def update_activity(self, guild_id: int) -> None:
        """Record the current UTC time as the latest activity for a guild.

        Args:
            guild_id (int): The Discord guild ID.
        """
        self.last_activity[guild_id] = datetime.now(timezone.utc)

    def clear_activity(self, guild_id: int) -> None:
        """Remove the activity timestamp for a guild.

        Args:
            guild_id (int): The Discord guild ID.
        """
        self.last_activity.pop(guild_id, None)

    def get_inactive_guilds(self) -> list[int]:
        """Return guild IDs whose last activity exceeds the inactivity threshold.

        Returns:
            list[int]: A list of guild IDs that should be disconnected.
        """
        now = datetime.now(timezone.utc)
        return [
            guild_id
            for guild_id, last_active in self.last_activity.items()
            if (now - last_active).total_seconds() > self.config.INACTIVITY_TIMER + self._song_length.get(guild_id, 0)
        ]

    # ------------------------------------------------------------------
    # Song-length tracking (per-guild inactivity grace period)
    # ------------------------------------------------------------------

    def add_song_length(self, guild_id: int, duration: int) -> None:
        """Accumulate a track's duration into the guild's inactivity grace period.

        Args:
            guild_id (int): The Discord guild ID.
            duration (int): Track duration in seconds.
        """
        self._song_length[guild_id] = self._song_length.get(guild_id, 0) + duration

    def clear_song_length(self, guild_id: int) -> None:
        """Reset the accumulated song length for a guild (e.g. after disconnect).

        Args:
            guild_id (int): The Discord guild ID.
        """
        self._song_length.pop(guild_id, None)

    # ------------------------------------------------------------------
    # File validation & track extraction
    # ------------------------------------------------------------------

    def validate_file(self, file_name: str, file_size: int) -> tuple[bool, str | None]:
        """Validate an uploaded audio file against configured limits.

        Args:
            file_name (str): The original filename of the attachment.
            file_size (int): The file size in bytes.

        Returns:
            tuple[bool,str|None]: A ``(valid, error_message)`` tuple. ``error_message`` is ``None``
            when the file is valid.
        """
        if not file_name.lower().endswith(self.config.AUDIO_TYPES):
            return False, f"Invalid file type! supported formats: `{', '.join(self.config.AUDIO_TYPES)}`"
        if file_size > self.config.MAX_FILE_SIZE:
            return False, f"File greater than 10MB!: `{(file_size / 1_000_000):.2f}`"
        return True, None

    async def extract_track_info(
        self, search: str | None, file_url: str | None, file_name: str | None
    ) -> tuple[Track | None, str | None]:
        """Extract track metadata from a search string or a Discord CDN URL.

        Args:
            search (str|None): A search query or direct URL.
            file_url (str|None): CDN URL of an uploaded audio file.
            file_name (str|None): Original filename of the uploaded audio file.

        Returns:
            tuple[Track|None,str|None]: A ``(track, error_message)`` tuple. On success ``error_message`` is
            ``None``; on failure ``track`` is ``None``.
        """
        if file_url and file_name:
            duration = await get_audio_duration(file_url)
            return Track(url=file_url, title=file_name, thumbnail_url=None, duration=duration), None

        if not search:
            return None, "You need to provide a search query or a file!"

        try:
            extractor = get_extractor(search=search)
            track = await extractor.extract(search=search, config=self.config)
            return track, None
        except Exception:
            logger.exception("Error extracting track info", extra={"search": search})
            return None, f"An error occurred while searching for: `{search}`"

    def get_ffmpeg_options(self, track: Track) -> dict[str, str]:
        """Return the appropriate FFmpeg options dict for a given track URL.

        Args:
            track (Track): The track whose URL determines streaming vs local options.

        Returns:
            dict[str,str]: A FFmpeg options dictionary suitable for :class:`discord.FFmpegOpusAudio`.
        """
        if "cdn.discordapp.com" in track.url or os.path.isfile(track.url):
            return self.config.LOCAL_FFMPEG_OPTIONS
        return self.config.STREAM_FFMPEG_OPTIONS
