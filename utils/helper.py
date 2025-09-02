import io
import json
import os
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import aiohttp
import discord
import soundfile as sf  # type: ignore
from discord.channel import VocalGuildChannel

from schemas.audio_model import AudioConfig


def load_config() -> AudioConfig:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "configs.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    conf = {
        "local_ffmpeg_options": config["ffmpeg"]["local"],
        "stream_ffmpeg_options": config["ffmpeg"]["stream"],
        "yt_dlp_options": config["ydl"],
        "audio_types": tuple(config["audio_types"]),
    }

    return AudioConfig(**conf)


def get_file_extension(url: str) -> tuple[str, str]:
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    base_name, file_extension = os.path.splitext(file_name)
    return base_name, file_extension.lower()


def convert_time(seconds: int | None) -> str:
    """
    Convert video duration from seconds to hh:mm:ss.

    Args:
        seconds (int | None): Duration in seconds of the video.

    Returns:
        str: Converted time as a string i.e. hh:mm:ss or mm:ss.
    """
    if seconds is None:
        return "Upload"
    minute, sec = divmod(seconds, 60)
    hour, minute = divmod(minute, 60)
    if hour > 0:
        return f"{hour}:{minute:02d}:{sec:02d}"
    return f"{minute:02d}:{sec:02d}"


async def get_audio_duration(url: str) -> int | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    audio_bytes = io.BytesIO(await response.read())
                    with sf.SoundFile(audio_bytes) as audio_file:
                        duration = len(audio_file) / audio_file.samplerate
                    return duration
                print(f"Failed to download audio file. Status code: {response.status}")
                return None
    except aiohttp.ClientError as e:
        print(f"An error occurred in 'get_audio_duration': {e}")
        return None


def get_user_voice_channel(interaction: discord.Interaction) -> VocalGuildChannel | None:
    if isinstance(interaction.user, discord.Member) and interaction.user.voice and interaction.user.voice.channel:
        return interaction.user.voice.channel
    return None


def clean_youtube_url(url: str) -> str:
    """
    Cleans YouTube URLs to remove playlist query param.

    Args:
        url (str): URL of YouTube video.

    Returns:
        str: The cleaned URL.
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    query_params.pop("list", None)

    new_query = urlencode(query_params, doseq=True)
    cleaned_url = urlunparse(parsed._replace(query=new_query))

    return cleaned_url
