from extractors.cdn_extractor import CdnExtractor
from extractors.soundcloud_extractor import SoundCloudExtractor
from extractors.youtube_extractor import YouTubeExtractor
from utils.track_extractor import TrackExtractor


def get_extractor(search: str) -> TrackExtractor:
    """Return the appropriate :class:`TrackExtractor` for the given search string.

    Args:
        search (str): A search query or URL string.

    Returns:
        TrackExtractor: A :class:`utils.track_extractor.TrackExtractor` instance.
    """
    if "soundcloud.com" in search:
        return SoundCloudExtractor()
    if "cdn.discordapp.com/attachments/" in search:
        return CdnExtractor()
    return YouTubeExtractor()
