import asyncio
import os

from discord.ext import commands
from dotenv import load_dotenv

from cogs.music_cog import MusicBot, intents
from cogs.name_cog import NameChanger
from utils.config import config_factory

config = config_factory()


class BotClient(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",  # Prefix still required but won't be used
            intents=intents,
        )

    async def setup_hook(self) -> None:
        await self.add_cog(MusicBot(self, config=config))
        await self.add_cog(NameChanger(self, config=config))
        await self.tree.sync()  # Sync slash commands with Discord

    async def on_ready(self) -> None:
        if self.user:
            print(f"Logged in as {self.user} (ID: {self.user.id})")
            print("")


async def main() -> None:
    async with BotClient() as client:
        token = os.getenv("DISCORD_TOKEN")
        if isinstance(token, str):
            await client.start(token)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
