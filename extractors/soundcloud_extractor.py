import yt_dlp

from schemas.track import Track
from utils.config_interface import ConfigInterface


class SoundCloudExtractor:
    async def extract(self, search: str, config: ConfigInterface) -> Track | None:
        with yt_dlp.YoutubeDL(config.YDL_OPTIONS.model_dump()) as ydl:
            info = ydl.extract_info(search, download=False)  # type: ignore
            return Track(
                url=info["url"],
                title=info["title"],
                thumbnail_url=info.get("thumbnail"),
                duration=info.get("duraction"),
            )
