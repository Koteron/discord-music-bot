import asyncio

import discord
from discord.ext import commands
from asyncio import run_coroutine_threadsafe
from urllib import parse, request
import re
from yt_dlp import YoutubeDL


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.music_queue = {}
        self.queue_index = {}

        self.YTDL_OPTIONS = {'format': 'bestaudio', 'nonplaylist': 'True'}

        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        self.vc = {}

        self.inactivity_task = {}

        self.INACTIVITY_TIME = 10

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.music_queue[guild.id] = []
            self.queue_index[guild.id] = 0
            self.inactivity_task[guild.id] = None
            self.vc[guild.id] = None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id != self.bot.user.id \
                and before.channel is not None \
                and after.channel != before.channel:
            remaining_channel_members = before.channel.members
            if len(remaining_channel_members) == 1 \
                    and remaining_channel_members[0].id == self.bot.user.id \
                    and self.vc[member.guild.id].is_connected():
                await self._leave_channel(member.guild.id)

    @commands.command(
        name="play",
        aliases=["pl"],
        help=""
    )
    async def play(self, ctx, *args):
        """ Play command is join and (resume or add and resume) """

        try:
            await self._join_vc(ctx)
        except:
            await ctx.send("You must be connected to a voice channel")
            return
        if not args:
            await self.resume(ctx)
        else:
            song = await self._add_song(ctx, *args)
            if len(self.music_queue[ctx.guild.id]) > 1:
                await ctx.send(embed=self._added_song_embed(ctx, song))
            if not self.vc[ctx.guild.id].is_playing():
                await self._play_music(ctx)

    @commands.command(
        name="add",
        aliases=["a"],
        help=""
    )
    async def add(self, ctx, *args):
        if not args:
            await ctx.send("You need to specify a song to be added")
        else:
            song = await self._add_song(ctx, *args)
            await ctx.send(embed=self._added_song_embed(ctx, song))

    @commands.command(
        name="pause",
        aliases=["ps", "stop"],
        help=""
    )
    async def pause(self, ctx):
        if not self.vc[ctx.guild.id]:
            await ctx.send("There is no audio to be played at the moment")
        elif self.vc[ctx.guild.id].is_playing():
            await ctx.send("Audio paused!")
            self.vc[ctx.guild.id].pause()

    @commands.command(
        name="resume",
        aliases=["rs"],
        help=""
    )
    async def resume(self, ctx):
        if self.vc[ctx.guild.id] is None or len(self.music_queue[ctx.guild.id]) == 0:
            await ctx.send("There is no audio to be played at the moment")
        elif self.vc[ctx.guild.id].is_paused():
            self.vc[ctx.guild.id].resume()
            await ctx.send("The audio is now playing!")
        else:
            await self._play_music(ctx)

    @commands.command(
        name="skip",
        aliases=["s"],
        help=""
    )
    async def skip(self, ctx):
        if self.vc[ctx.guild.id] is None or len(self.music_queue[ctx.guild.id]) == 0:
            await ctx.send("There is no audio playing at the moment")
            return
        self.vc[ctx.guild.id].stop()
        await ctx.send("Skipped song!")

    @commands.command(
        name="join",
        aliases=["j"],
        help=""
    )
    async def join(self, ctx):
        if ctx.author.voice:
            await self._join_vc(ctx)
            await ctx.send(f"The bot has joined {ctx.author.voice.channel}")
        else:
            await ctx.send("Connect to a voice channel first")

    @commands.command(
        name="leave",
        aliases=["l"],
        help=""
    )
    async def leave(self, ctx):
        if self.vc[ctx.guild.id] is not None:
            await self._leave_channel(ctx.guild.id)
            await ctx.send(f"The bot has left {ctx.author.voice.channel}")

    @staticmethod
    def _now_playing_embed(ctx, song):
        embed = discord.Embed(
            title="Now Playing",
            description=f'[{song["title"]}]({song["link"]})',
            colour=discord.Color.blue()
        )
        embed.set_thumbnail(url=song["thumbnail"])
        embed.set_footer(text=f'song added by: {str(ctx.author)}', icon_url=ctx.author.avatar.url)

        return embed

    @staticmethod
    def _added_song_embed(ctx, song):
        embed = discord.Embed(
            title="Added song to queue",
            description=f'[{song["title"]}]({song["link"]})',
            colour=discord.Color.red()
        )
        embed.set_thumbnail(url=song["thumbnail"])
        embed.set_footer(text=f'song added by: {str(ctx.author)}', icon_url=ctx.author.avatar.url)

        return embed

    @staticmethod
    def _search_yt(search):
        query_string = parse.urlencode({'search_query': search})
        html_content = request.urlopen(
            'http://www.youtube.com/results?' + query_string
        )
        search_results = re.findall(r'/watch\?v=(.{11})', html_content.read().decode())
        return search_results[:10]

    async def _join_vc(self, ctx):
        if self.vc[ctx.guild.id] is None or not self.vc[ctx.guild.id].is_connected():
            self.vc[ctx.guild.id] = await ctx.author.voice.channel.connect()

            if self.vc[ctx.guild.id] is None:
                await ctx.send("Could not connect to the voice channel")
                return
        else:
            if self.vc[ctx.guild.id] != ctx.author.voice.channel:
                await self.vc[ctx.guild.id].move_to(ctx.author.voice.channel)

    def _extract_yt(self, video_id):
        with YoutubeDL(self.YTDL_OPTIONS) as ytdl:
            try:
                info = ytdl.extract_info(video_id, download=False)
            except:
                return None
        return {
            'link': 'http://www.youtube.com/watch?v=' + video_id,
            'thumbnail': 'https://i.ytimg.com/vi/' + video_id +
                         '/hqdefault.jpg?sqp=-oaymwEcCOADEI4CSFXyq4qpAw4IARUAAIhCGAFwAcABBg='
                         '=&rs=AOn4CLD5uL4xKN-IUfez6KIW_j5y70mlig',
            'source': info.get('url'),
            'title': info['title']
        }

    def _play_next(self, ctx):
        if self.vc[ctx.guild.id].is_paused():
            return
        if self.inactivity_task[ctx.guild.id] is not None \
                and not self.inactivity_task[ctx.guild.id].done():
            self.inactivity_task[ctx.guild.id].cancel()
        if self.queue_index[ctx.guild.id] + 1 < len(self.music_queue[ctx.guild.id]):
            self.queue_index[ctx.guild.id] += 1

            coro = self._play_music(ctx)
            fut = run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except:
                pass
        else:
            self.queue_index[ctx.guild.id] += 1
            self.inactivity_task[ctx.guild.id] = \
                run_coroutine_threadsafe(self._delayed_leave(ctx), self.bot.loop)

    async def _delayed_leave(self, ctx):
        try:
            await asyncio.sleep(self.INACTIVITY_TIME)
            await self.leave(ctx)
        except asyncio.CancelledError:
            print("Execution interrupted")

    async def _play_music(self, ctx):
        if self.inactivity_task[ctx.guild.id] is not None \
                and not self.inactivity_task[ctx.guild.id].done():
            self.inactivity_task[ctx.guild.id].cancel()
        if self.queue_index[ctx.guild.id] < len(self.music_queue[ctx.guild.id]):

            song = self.music_queue[ctx.guild.id][self.queue_index[ctx.guild.id]]

            await ctx.send(embed=self._now_playing_embed(ctx, song))

            self.vc[ctx.guild.id].play(
                discord.FFmpegPCMAudio(song['source'], **self.FFMPEG_OPTIONS),
                after=lambda o: self._play_next(ctx)
            )
        else:
            await ctx.send("There are no songs in the queue to be played")
            self.queue_index[ctx.guild.id] = 1


    async def _add_song(self, ctx, *args):
            search_results = self._search_yt(" ".join(args))

            if not search_results:
                await ctx.send("Could not find the song. Try different keywords.")
                return None

            song = self._extract_yt(search_results[0])

            if song is None:
                await ctx.send("Could not download the song, incorrect format.")
            else:
                if ctx.guild.id not in self.music_queue:
                    self.music_queue[ctx.guild.id] = []
                    
                self.music_queue[ctx.guild.id].append(song)
                return song

    async def _leave_channel(self, guild_id):
        if self.vc[guild_id] is None:
            return
        await self.vc[guild_id].disconnect()
        self.vc[guild_id] = None
        self.music_queue[guild_id] = []
        self.queue_index[guild_id] = 0

