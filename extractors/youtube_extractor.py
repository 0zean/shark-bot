import asyncio

import yt_dlp

from schemas.track import Track
from utils.config_interface import ConfigInterface
from utils.helper import clean_youtube_url


class YouTubeExtractor:
    async def extract(self, search: str, config: ConfigInterface) -> Track | None:
        def _extract():
            with yt_dlp.YoutubeDL(config.YDL_OPTIONS.model_dump()) as ydl:
                cleaned_search = clean_youtube_url(url=search)
                return ydl.extract_info(f"ytsearch:{cleaned_search}", download=False)

        info = await asyncio.to_thread(_extract)
        if info and "entries" in info and info["entries"]:
            entry = info["entries"][0]  # type: ignore
            return Track(
                url=entry["url"],
                title=entry["title"],
                thumbnail_url=f"https://img.youtube.com/vi/{entry['id']}/default.jpg",
                duration=entry.get("duration"),
            )
        return None
