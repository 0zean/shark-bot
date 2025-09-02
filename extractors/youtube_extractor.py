import yt_dlp

from schemas.track import Track
from utils.config_interface import ConfigInterface
from utils.helper import clean_youtube_url


class YouTubeExtractor:
    async def extract(self, search: str, config: ConfigInterface) -> Track | None:
        with yt_dlp.YoutubeDL(config.YDL_OPTIONS.model_dump()) as ydl:
            cleaned_search = clean_youtube_url(url=search)
            info = ydl.extract_info(f"ytsearch:{cleaned_search}", download=False)
            if "entries" in info:
                info = info["entries"][0]  # type: ignore
                return Track(
                    url=info["url"],
                    title=info["title"],
                    thumbnail_url=f"https://img.youtube.com/vi/{info['id']}/default.jpg",
                    duration=info["duration"],
                )
