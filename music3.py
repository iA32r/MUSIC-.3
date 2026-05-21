import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from aiohttp import web

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True
}

queues = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

async def play_next(ctx):
    guild_id = ctx.guild.id
    if guild_id not in queues or len(queues[guild_id]) == 0:
        return
    vc = ctx.voice_client
    if not vc:
        return
    url, title = queues[guild_id].pop(0)
    source = discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
    def after(error):
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    vc.play(source, after=after)
    await ctx.send(f"Now playing: {title}")

@bot.command()
async def play(ctx, *, search):
    # لازم المستخدم يكون في فويس
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("You must be in a voice channel")
        return
    guild_id = ctx.guild.id
    vc = ctx.voice_client
    # يدخل نفس روم المستخدم أو يتحرك له
    if not vc:
        vc = await ctx.author.voice.channel.connect(self_deaf=True)
    else:
        if vc.channel != ctx.author.voice.channel:
            await vc.move_to(ctx.author.voice.channel)
    if guild_id not in queues:
        queues[guild_id] = []
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(search, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        url = info['url']
        title = info.get('title', 'Unknown')
    queues[guild_id].append((url, title))
    await ctx.send(f"Added to queue: {title}")
    if not vc.is_playing():
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped")

@bot.command()
async def queue(ctx):
    guild_id = ctx.guild.id
    if guild_id not in queues or len(queues[guild_id]) == 0:
        await ctx.send("Queue is empty")
        return
    songs = "\n".join([t for _, t in queues[guild_id]])
    await ctx.send(f"Queue:\n{songs}")

# ← هذا الجديد فقط
async def health(request):
    return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get('/', health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()
    await bot.start(os.environ.get("DISCORD_TOKEN"))

asyncio.run(main())
