import logging
from pathlib import Path
from random import choice

logger = logging.getLogger(__name__)


class NameService:
    def __init__(self):
        try:
            self.names = [name.strip() for name in Path("firstnames.txt").read_text("utf-8").splitlines()]
            self.towns = [town.strip() for town in Path("towns.txt").read_text("utf-8").splitlines()]
        except FileNotFoundError as e:
            logger.error(f"Could not load required data files for NameService: {e}")
            self.names = ["Unknown"]
            self.towns = ["Nowhere"]

    def generate_random_nickname(self) -> str:
        """Generate a random nickname using loaded names and towns."""
        return f"{choice(self.names)} from {choice(self.towns)}"
