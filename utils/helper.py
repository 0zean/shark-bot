import json
import os
from urllib.parse import urlparse


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
