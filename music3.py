import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import traceback
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
    'quiet': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0'
}

queues = {}
VOICE_CHANNEL_ID = 1505282531858317382

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

async def fetch_info(search: str):
    loop = asyncio.get_event_loop()
    def _extract():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(search, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            return info['url'], info.get('title', 'Unknown')
    return await loop.run_in_executor(None, _extract)

async def play_next(ctx):
    guild_id = ctx.guild.id

    if guild_id not in queues or len(queues[guild_id]) == 0:
        return

    vc = ctx.voice_client
    if not vc or not vc.is_connected():
        return

    url, title = queues[guild_id].pop(0)

    try:
        source = discord.FFmpegOpusAudio(url, **FFMPEG_OPTIONS)
    except Exception as e:
        await ctx.send(f"Error loading audio: {e}")
        traceback.print_exc()
        await play_next(ctx)
        return

    def after(error):
        if error:
            print(f"[after error] {error}")
            traceback.print_exc()
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    vc.play(source, after=after)
    await ctx.send(f"Now playing: {title}")

@bot.command()
async def play(ctx, *, search):
    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if not vc:
        channel = bot.get_channel(VOICE_CHANNEL_ID)
        if not channel:
            await ctx.send("Could not find voice channel")
            return
        vc = await channel.connect(self_deaf=True)
    elif vc.channel.id != VOICE_CHANNEL_ID:
        channel = bot.get_channel(VOICE_CHANNEL_ID)
        await vc.move_to(channel)

    if guild_id not in queues:
        queues[guild_id] = []

    try:
        url, title = await fetch_info(search)
    except Exception as e:
        await ctx.send(f"Could not find: {search}\nError: {e}")
        traceback.print_exc()
        return

    queues[guild_id].append((url, title))
    await ctx.send(f"Added to queue: {title}")

    if not vc.is_playing():
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped")
    else:
        await ctx.send("Nothing is playing")

@bot.command()
async def queue(ctx):
    guild_id = ctx.guild.id
    if guild_id not in queues or len(queues[guild_id]) == 0:
        await ctx.send("Queue is empty")
        return
    songs = "\n".join([f"{i+1}. {t}" for i, (_, t) in enumerate(queues[guild_id])])
    await ctx.send(f"Queue:\n{songs}")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        queues.pop(ctx.guild.id, None)
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected")

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"Error: {error}")
    traceback.print_exc()

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
