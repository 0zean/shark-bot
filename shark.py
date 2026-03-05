import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load env vars first — before any os.getenv() or config_factory() calls
load_dotenv()

from cogs.music_cog import MusicBot  # noqa: E402
from cogs.name_cog import NameChanger  # noqa: E402
from services.music_service import MusicService  # noqa: E402
from services.name_service import NameService  # noqa: E402
from utils.config import config_factory  # noqa: E402

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("shark_bot")

# Intialize intents at entry
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

config = config_factory()


class BotClient(commands.Bot):
    """Main bot client. Loads cogs and syncs slash commands on startup."""

    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",  # Prefix still required but slash commands are primary
            intents=intents,
        )

    async def setup_hook(self) -> None:
        """Called by discord.py before the bot connects. Registers cogs."""
        music_service = MusicService(config)
        name_service = NameService()

        await self.add_cog(MusicBot(self, config=config, music_service=music_service))
        await self.add_cog(NameChanger(self, config=config, name_service=name_service))
        await self.tree.sync()

    async def on_ready(self) -> None:
        """Fired once the bot is connected and ready."""
        if self.user:
            logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)


async def main() -> None:
    """Entry point: validates token then starts the bot."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN environment variable is missing or empty. Set it in your .env file before starting the bot."
        )

    async with BotClient() as client:
        await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
