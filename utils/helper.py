import io
import json
import logging
import os
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import aiohttp
import discord
import soundfile as sf  # type: ignore[import-untyped]
from discord.channel import VocalGuildChannel

from schemas.audio_model import AudioConfig

logger = logging.getLogger(__name__)

# Default timeout applied to all outbound HTTP requests in this module
_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)


def load_config() -> AudioConfig:
    """Load bot audio configuration from the bundled JSON file.

    Returns:
        A validated :class:`schemas.audio_model.AudioConfig` instance.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "configs.json")

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    conf = {
        "local_ffmpeg_options": config["ffmpeg"]["local"],
        "stream_ffmpeg_options": config["ffmpeg"]["stream"],
        "yt_dlp_options": config["ydl"],
        "audio_types": tuple(config["audio_types"]),
    }

    return AudioConfig(**conf)


def get_file_extension(url: str) -> tuple[str, str]:
    """Extract the base filename and lowercased extension from a URL.

    Args:
        url: A fully-qualified URL string.

    Returns:
        A ``(base_name, extension)`` tuple, e.g. ``("song", ".mp3")``.
    """
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    base_name, file_extension = os.path.splitext(file_name)
    return base_name, file_extension.lower()


def convert_time(seconds: int | None) -> str:
    """Convert a duration in seconds to a human-readable ``hh:mm:ss`` string.

    Args:
        seconds: Duration in seconds, or ``None`` for uploaded files.

    Returns:
        A formatted time string such as ``"3:45"`` or ``"1:02:30"``.
        Returns ``"Upload"`` when *seconds* is ``None``.
    """
    if seconds is None:
        return "Upload"
    minute, sec = divmod(seconds, 60)
    hour, minute = divmod(minute, 60)
    if hour > 0:
        return f"{hour}:{minute:02d}:{sec:02d}"
    return f"{minute:02d}:{sec:02d}"


async def get_audio_duration(
    url: str,
    *,
    session: aiohttp.ClientSession | None = None,
) -> int | None:
    """Fetch and return the duration of a remote audio file in seconds.

    Args:
        url: URL of the audio file to inspect.
        session: An optional pre-existing :class:`aiohttp.ClientSession` to
            reuse. When ``None`` a new session with a 10 s timeout is created
            for this call only.

    Returns:
        Rounded duration in seconds, or ``None`` if the file cannot be read.
    """

    async def _fetch(client: aiohttp.ClientSession) -> int | None:
        try:
            async with client.get(url) as response:
                if response.status != 200:
                    logger.warning("Failed to download audio file — HTTP %s", response.status, extra={"url": url})
                    return None
                audio_bytes = io.BytesIO(await response.read())
                with sf.SoundFile(audio_bytes) as audio_file:
                    duration = len(audio_file) / audio_file.samplerate
                return round(duration)
        except aiohttp.ClientError as e:
            logger.error("HTTP error in get_audio_duration", exc_info=e, extra={"url": url})
            return None

    if session is not None:
        return await _fetch(session)

    async with aiohttp.ClientSession(timeout=_DEFAULT_TIMEOUT) as new_session:
        return await _fetch(new_session)


def get_user_voice_channel(interaction: discord.Interaction) -> VocalGuildChannel | None:
    """Return the voice channel the interaction user is currently in.

    Args:
        interaction: The Discord interaction.

    Returns:
        The user's :class:`discord.channel.VocalGuildChannel`, or ``None``.
    """
    if isinstance(interaction.user, discord.Member) and interaction.user.voice and interaction.user.voice.channel:
        return interaction.user.voice.channel
    return None


def clean_youtube_url(url: str) -> str:
    """Strip the ``list`` (playlist) query parameter from a YouTube URL.

    Args:
        url: A YouTube video URL, potentially containing playlist parameters.

    Returns:
        The cleaned URL with the ``list`` query parameter removed.
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    query_params.pop("list", None)
    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
