from pydantic import BaseModel, Field


class YtDLP(BaseModel):
    format: str = Field(description="yt-dlp format")
    noplaylist: bool = Field(description="Whether to allow playlist links or not")
    cookiefile: str = Field(description="Static YT cookie file")


class AudioConfig(BaseModel):
    local_ffmpeg_options: dict[str, str]
    stream_ffmpeg_options: dict[str, str]
    yt_dlp_options: YtDLP
    audio_types: tuple[str, ...]
