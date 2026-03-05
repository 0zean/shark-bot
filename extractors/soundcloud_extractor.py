import asyncio

import yt_dlp

from schemas.track import Track
from utils.config_interface import ConfigInterface


class SoundCloudExtractor:
    """Extract a :class:`Track` from a SoundCloud URL."""

    async def extract(self, search: str, config: ConfigInterface) -> Track | None:
        """
        Build a Track from a SoundCloud URL.

        Args:
            search (str): SoundCloud URL.
            config (ConfigInterface): Bot configuration (provides supported audio types).

        Returns:
            Track|None: A :class:`Track` if the URL is a supported audio type,
            otherwise ``None``.
        """

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
