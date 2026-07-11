import asyncio
import os
import tempfile

import yt_dlp

from schemas.track import Track
from utils.config import BotConfig
from utils.helper import clean_youtube_url

DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), "shark_bot_audio")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class YouTubeExtractor:
    """Extract a :class:`Track` from a YouTube URL by downloading the audio locally."""

    async def extract(self, search: str, config: BotConfig) -> Track | None:
        """
        Download audio from a YouTube URL and build a Track pointing to the local file.

        Args:
            search (str): YouTube URL or search query.
            config (ConfigInterface): Bot configuration (provides yt-dlp options).

        Returns:
            Track|None: A :class:`Track` pointing to the downloaded file,
            or ``None`` if extraction failed.
        """

        def _extract() -> dict[str, str | int | None] | None:
            opts = config.YDL_OPTIONS.model_dump()
            opts["outtmpl"] = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")

            with yt_dlp.YoutubeDL(opts) as ydl:
                cleaned_search = clean_youtube_url(url=search)
                info = ydl.extract_info(f"ytsearch:{cleaned_search}", download=True)
                if info and "entries" in info and info["entries"]:
                    entry = info["entries"][0]
                    filepath = ydl.prepare_filename(entry)
                    return {
                        "filepath": filepath,
                        "title": entry["title"],
                        "id": entry["id"],
                        "duration": entry.get("duration"),
                    }
                return None

        result = await asyncio.to_thread(_extract)
        if result and result.get("filepath"):
            return Track(
                url=str(result["filepath"]),
                title=str(result["title"]),
                thumbnail_url=f"https://img.youtube.com/vi/{result['id']}/default.jpg",
                duration=int(result["duration"]) if result.get("duration") is not None else None,
            )
        return None
