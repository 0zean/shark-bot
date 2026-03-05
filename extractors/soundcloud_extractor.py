import yt_dlp
import asyncio

from schemas.track import Track
from utils.config_interface import ConfigInterface


class SoundCloudExtractor:
    async def extract(self, search: str, config: ConfigInterface) -> Track | None:
        def _extract():
            with yt_dlp.YoutubeDL(config.YDL_OPTIONS.model_dump()) as ydl:
                return ydl.extract_info(search, download=False)  # type: ignore

        info = await asyncio.to_thread(_extract)
        if info:
            return Track(
                url=info["url"],
                title=info["title"],
                thumbnail_url=info.get("thumbnail"),
                duration=info.get("duration"),
            )
        return None
