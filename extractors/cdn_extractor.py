from schemas.track import Track
from utils.config_interface import ConfigInterface
from utils.helper import get_audio_duration, get_file_extension


class CdnExtractor:
    async def extract(self, search: str, config: ConfigInterface) -> Track | None:
        track_name, cdn_ext = get_file_extension(search)
        if cdn_ext in config.AUDIO_TYPES:
            duration = await get_audio_duration(search)
            return Track(url=search, title=track_name, thumbnail_url=None, duration=duration)
