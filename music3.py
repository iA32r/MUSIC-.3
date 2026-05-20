import discord
from discord.ext import commands
import yt_dlp

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 🔥 حط آيديات الرومات
VOICE_CHANNEL_ID = 1505282531858317382
COMMAND_CHANNEL_ID = 1505282531858317382

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True
}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # 🎥 حالة Streaming
    await bot.change_presence(
        activity=discord.Streaming(
            name="Silent Error",
            url="https://twitch.tv/discord"
        )
    )

    # 🔊 دخول الروم الصوتي تلقائي
    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if channel and isinstance(channel, discord.VoiceChannel):
        try:
            if not channel.guild.voice_client:
                await channel.connect(self_deaf=True)
            print("Connected to voice channel")
        except Exception as e:
            print(f"Voice join error: {e}")


@bot.command()
async def play(ctx, *, search):
    # 🚫 يشتغل فقط في روم معين
    if ctx.channel.id != COMMAND_CHANNEL_ID:
        return

    vc = ctx.voice_client

    # يدخل الروم إذا مو موجود
    if not vc:
        vc = await ctx.author.voice.channel.connect(self_deaf=True)

    # 🔍 جلب الصوت من يوتيوب
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(search, download=False)

        if 'entries' in info:
            info = info['entries'][0]

        url = info['url']
        title = info.get('title', 'Unknown')

    # ⛔ إيقاف أي صوت شغال
    if vc.is_playing():
        vc.stop()

    # 🎧 تشغيل Streaming
    source = await discord.FFmpegOpusAudio.from_probe(
        url,
        **FFMPEG_OPTIONS
    )

    vc.play(source)

    await ctx.send(f"🎵 Now Streaming: **{title}**")


bot.run("")
