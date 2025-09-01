from typing import Protocol

from schemas.track import Track
from utils.config_interface import ConfigInterface


class TrackExtractor(Protocol):
    async def extract(self, search: str, config: ConfigInterface) -> Track | None: ...
