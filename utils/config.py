from schemas.audio_model import AudioConfig
from utils.helper import load_config


class BotConfig:
    def __init__(self, config_data: AudioConfig):
        self.LOCAL_FFMPEG_OPTIONS = config_data.local_ffmpeg_options
        self.STREAM_FFMPEG_OPTIONS = config_data.stream_ffmpeg_options
        self.YDL_OPTIONS = config_data.yt_dlp_options
        self.AUDIO_TYPES = config_data.audio_types

        self.DELETE_TIMER = 3
        self.INACTIVITY_TIMER = 600
        self.MAX_FILE_SIZE = 10485760
