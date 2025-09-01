from abc import ABC

from schemas.audio_model import YtDLP


class ConfigInterface(ABC):
    LOCAL_FFMPEG_OPTIONS: dict[str, str]
    STREAM_FFMPEG_OPTIONS: dict[str, str]
    YDL_OPTIONS: YtDLP
    AUDIO_TYPES: tuple[str, ...]
    DELETE_TIMER: int
    INACTIVITY_CHECK: int
    INACTIVITY_TIMER: int
    MAX_FILE_SIZE: int
