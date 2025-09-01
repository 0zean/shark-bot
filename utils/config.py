from schemas.audio_model import AudioConfig
from utils.config_interface import ConfigInterface
from utils.helper import load_config


class BotConfig(ConfigInterface):
    def __init__(self, config_data: AudioConfig):
        self.LOCAL_FFMPEG_OPTIONS = config_data.local_ffmpeg_options
        self.STREAM_FFMPEG_OPTIONS = config_data.stream_ffmpeg_options
        self.YDL_OPTIONS = config_data.yt_dlp_options
        self.AUDIO_TYPES = config_data.audio_types

        self.DELETE_TIMER = 3
        self.INACTIVITY_TIMER = 600
        self.MAX_FILE_SIZE = 10485760


def config_factory(source: str = "default", **kwargs) -> ConfigInterface:
    """
    Factory function to create a config object.

    Args:
        source (str): The source of the config.
        **kwargs: Additional keyword arguments.

    Raises:
        ValueError: If the config source is invalid.

    Returns:
        ConfigInterface: The config object.
    """
    if source == "default":
        config_data = load_config()
        return BotConfig(config_data=config_data)
    elif source == "dict":
        return BotConfig(config_data=kwargs["config_data"])
    raise ValueError(f"Invalid config source: {source}")
