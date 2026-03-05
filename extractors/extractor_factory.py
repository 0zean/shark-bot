from extractors.cdn_extractor import CdnExtractor
from extractors.soundcloud_extractor import SoundCloudExtractor
from extractors.youtube_extractor import YouTubeExtractor
from utils.track_extractor import TrackExtractor


def get_extractor(search: str) -> TrackExtractor:
    """Return the appropriate :class:`TrackExtractor` for the given search string.

    Selection is based on URL pattern matching:
    - SoundCloud URLs → :class:`SoundCloudExtractor`
    - Discord CDN attachment URLs → :class:`CdnExtractor`
    - Everything else → :class:`YouTubeExtractor` (search or direct YT URL)

    Args:
        search: A search query or URL string.

    Returns:
        A :class:`utils.track_extractor.TrackExtractor` instance.
    """
    if "soundcloud.com" in search:
        return SoundCloudExtractor()
    if "cdn.discordapp.com/attachments/" in search:
        return CdnExtractor()
    return YouTubeExtractor()
