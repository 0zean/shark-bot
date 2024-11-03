import asyncio
import os

import discord
import yt_dlp
from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True

FFMPEG_OPTIONS = {"options": "-vn"}
YDL_OPTIONS = {
    "format": "bestaudio",
    "noplaylist": True,
    "username": "oauth",
    "password": "",
}

client = commands.Bot(command_prefix="+", intents=intents)

load_dotenv()


class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = []

    @commands.command()
    async def play(self, ctx, *, search):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("You're not in a voice channel.")

        try:
            if not ctx.voice_client:
                await voice_channel.connect()
        except discord.errors.ClientException:
            return await ctx.send(
                "Error connecting to voice channel. Please try again."
            )

        async with ctx.typing():
            try:
                with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(f"ytsearch:{search}", download=False)
                    if "entries" in info:
                        info = info["entries"][0]
                    url = info["url"]
                    title = info["title"]
                    id = info["id"]
                    self.queue.append((url, title, id))
                    await ctx.send(f"Added to queue: **{title}**")
            except Exception as e:
                await ctx.send(
                    f"An error occurred while processing your request: {str(e)}"
                )
                return

        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)

    async def play_next(self, ctx):
        if self.queue:
            url, title, id = self.queue.pop(0)

            try:
                source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)

                def after_playing(error):
                    if error:
                        print(f"Error in playback: {error}")
                    asyncio.run_coroutine_threadsafe(
                        self.play_next(ctx), self.client.loop
                    )

                ctx.voice_client.play(
                    source,
                    after=after_playing,
                )

                em1 = discord.Embed(
                    title=f"Now playing **{title}**", color=ctx.author.color
                )

                em1.set_thumbnail(
                    url=f"https://img.youtube.com/vi/{id}/default.jpg".format(
                        videoID=id
                    )
                )

                await ctx.send(embed=em1)

            except Exception as e:
                await ctx.send(f"Error playing {title}: {str(e)}")
                await self.play_next(ctx)

        elif not ctx.voice_client.is_playing():
            await ctx.send("Queue is empty.")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped!")

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.queue.clear()
            await ctx.send("Disconnected from voice channel.")

        else:
            await ctx.send("I'm not in a voice channel!")


async def main():
    async with client:
        await client.add_cog(MusicBot(client))
        await client.start(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())
