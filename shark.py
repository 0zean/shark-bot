import asyncio
import os

from discord.ext import commands
from dotenv import load_dotenv

from cogs.music_cog import MusicBot, intents


class BotClient(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",  # Prefix still required but won't be used
            intents=intents,
        )

    async def setup_hook(self):
        await self.add_cog(MusicBot(self))
        await self.tree.sync()  # Sync slash commands with Discord

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("")


async def main():
    async with BotClient() as client:
        await client.start(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
