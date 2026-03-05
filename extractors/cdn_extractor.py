from schemas.track import Track
from utils.config_interface import ConfigInterface
from utils.helper import get_audio_duration, get_file_extension


class CdnExtractor:
    """Extract a :class:`Track` from a Discord CDN audio attachment URL."""

    async def extract(self, search: str, config: ConfigInterface) -> Track | None:
        """Build a Track from a Discord CDN audio URL.

        Args:
            search (str): The Discord CDN attachment URL.
            config (ConfigInterface): Bot configuration (provides supported audio types).

        Returns:
            Track|None: A :class:`Track` if the URL has a supported audio extension,
            otherwise ``None``.
        """
        track_name, cdn_ext = get_file_extension(search)
        if cdn_ext in config.AUDIO_TYPES:
            duration = await get_audio_duration(search)
            return Track(url=search, title=track_name, thumbnail_url=None, duration=duration)
        return None
