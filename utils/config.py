from helper import load_config

_config = load_config()


class BotConfig:
    LOCAL_FFMPEG_OPTIONS = _config.local_ffmpeg_options
    STREAM_FFMPEG_OPTIONS = _config.stream_ffmpeg_options
    YDL_OPTIONS = _config.yt_dlp_options
    AUDIO_TYPES = _config.audio_types

    delete_timer = 3
    inactivity_check = 60
    inactivity_timer = 600
    max_file_size = 10485760


config = BotConfig()
