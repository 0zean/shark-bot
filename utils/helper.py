import asyncio
import io
import json
import os
from urllib.parse import urlparse

import aiohttp
import soundfile as sf


def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "configs.json")

    with open(config_path, "r") as f:
        config = json.load(f)

    return {
        "LOCAL_FFMPEG_OPTIONS": config["ffmpeg"]["local"],
        "STREAM_FFMPEG_OPTIONS": config["ffmpeg"]["stream"],
        "YDL_OPTIONS": config["ydl"],
        "AUDIO_TYPES": tuple(config["audio_types"]),
    }


def get_file_extension(url: str) -> tuple[str, str]:
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    base_name, file_extension = os.path.splitext(file_name)
    return base_name, file_extension.lower()


def convert(seconds: int | None) -> str:
    if seconds is None:
        return "Upload"
    min, sec = divmod(seconds, 60)
    hour, min = divmod(min, 60)
    if hour > 0:
        return '%d:%02d:%02d' % (hour, min, sec)
    else:
        return '%02d:%02d' % (min, sec)


async def get_audio_duration(url: str) -> int | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    audio_bytes = io.BytesIO(await response.read())
                    with sf.SoundFile(audio_bytes) as audio_file:
                        duration = len(audio_file) / audio_file.samplerate
                    return duration
                else:
                    print(f"Failed to download audio file. Status code: {response.status}")
                    return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
