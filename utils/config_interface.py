from abc import ABC

from schemas.audio_model import YtDLP


class ConfigInterface(ABC):
    """Abstract base class defining the configuration contract for the bot.

    Concrete implementations (e.g. :class:`utils.config.BotConfig`) must
    provide all of the attributes declared here.
    """

    LOCAL_FFMPEG_OPTIONS: dict[str, str]
    STREAM_FFMPEG_OPTIONS: dict[str, str]
    YDL_OPTIONS: YtDLP
    AUDIO_TYPES: tuple[str, ...]
    DELETE_TIMER: int
    INACTIVITY_TIMER: int
    MAX_FILE_SIZE: int
