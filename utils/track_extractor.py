from typing import Protocol

from schemas.track import Track
from utils.config import BotConfig


class TrackExtractor(Protocol):
    async def extract(self, search: str, config: BotConfig) -> Track | None: ...
