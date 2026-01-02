import os
import discord
import asyncio
from discord.ext import commands

from music_cog import MusicCog

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or('!'),
    description='Relatively simple music bot example',
    intents=intents,
)


async def add_cog():
    await bot.add_cog(MusicCog(bot))


if __name__ == "__main__":
    asyncio.run(add_cog())
    bot.run(DISCORD_TOKEN)
