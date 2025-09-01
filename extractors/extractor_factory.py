from extractors.cdn_extractor import CdnExtractor
from extractors.soundcloud_extractor import SoundCloudExtractor
from extractors.youtube_extractor import YouTubeExtractor

Extractor = CdnExtractor | SoundCloudExtractor | YouTubeExtractor


def get_extractor(search: str) -> Extractor:
    if "soundcloud.com" in search:
        return SoundCloudExtractor()
    if "cdn.discordapp.com/attachments/" in search:
        return CdnExtractor()
    return YouTubeExtractor()
