import discord
from discord.ext import commands, tasks
import os
import requests
import youtube_dl
from discord import FFmpegPCMAudio
import asyncio

# ==========================
# INTENCJE
# ==========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================
# TWITCH API
# ==========================
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL")
TWITCH_TOKEN = None
IS_LIVE = False

DISCORD_CHANNEL_NAME = "general"  # zmień na swój kanał Discord

# ==========================
# KOLEJKA MUZYCZNA
# ==========================
music_queue = []

def play_next(ctx):
    if music_queue:
        url = music_queue.pop(0)
        ydl_opts = {'format': 'bestaudio'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            ctx.voice_client.play(FFmpegPCMAudio(url2), after=lambda e: play_next(ctx))
            coro = ctx.send(f"Odtwarzam: {info['title']}")
            asyncio.ensure_future(coro)
    else:
        coro = ctx.send("🎵 Kolejka zakończona.")
        asyncio.ensure_future(coro)

# ==========================
# PODSTAWOWE KOMENDY
# ==========================
@bot.event
async def on_ready():
    print(f"Bot zalogowany jako {bot.user}")
    get_twitch_token.start()
    check_stream.start()

@bot.command()
async def hej(ctx):
    await ctx.send(f"Hej {ctx.author.mention}! 👋 Miło Cię widzieć!")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong 🏓")

@bot.command()
async def helpme(ctx):
    await ctx.send(
        "📖 Komendy:\n"
        "!hej - powitanie\n"
        "!ping - sprawdzenie czy bot działa\n"
        "!live - info o starcie streama\n"
        "!socials - linki do sociali\n"
        "!clip - przypomnienie o klipach\n"
        "!addstreamerrole @nick - nadaje rolę Streamer Online\n"
        "!removestreamerrole @nick - usuwa rolę Streamer Online\n"
        "!join - bot wchodzi do kanału głosowego\n"
        "!leave - bot wychodzi z kanału\n"
        "!play <link> - dodaje do kolejki i odtwarza muzykę\n"
        "!skip - pomija aktualną piosenkę\n"
        "!queue - pokazuje kolejkę\n"
        "!pause - pauza\n"
        "!resume - wznawia\n"
        "!stop - zatrzymuje muzykę"
    )

# ==========================
# STREAMERSKIE KOMENDY
# ==========================
@bot.command()
async def live(ctx):
    await ctx.send(f"🔴 Stream {TWITCH_CHANNEL} właśnie wystartował! Dołączcie i oglądajcie!")

@bot.command()
async def socials(ctx):
    await ctx.send(
        "📱 Znajdziesz nas tutaj:\n"
        f"Twitch: https://twitch.tv/{TWITCH_CHANNEL}\n"
        "YouTube: https://youtube.com/TwojProfil\n"
        "Instagram: https://instagram.com/TwojProfil"
    )

@bot.command()
async def clip(ctx):
    await ctx.send("🎬 Nie zapomnijcie nagrywać klipów i oznaczać nas!")

# ==========================
# ROLE STREAMERA
# ==========================
@bot.command()
async def addstreamerrole(ctx, member: discord.Member):
    role_name = "Streamer Online"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        role = await ctx.guild.create_role(name=role_name)
        await ctx.send(f"Utworzono nową rolę: {role_name}")
    await member.add_roles(role)
    await ctx.send(f"Role {role_name} nadano {member.mention}")

@bot.command()
async def removestreamerrole(ctx, member: discord.Member):
    role_name = "Streamer Online"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"Role {role_name} usunięto {member.mention}")
    else:
        await ctx.send(f"{member.mention} nie ma roli {role_name}")

# ==========================
# MUZYKA
# ==========================
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("Musisz być w kanale głosowym!")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("Bot nie jest w żadnym kanale!")

@bot.command()
async def play(ctx, url):
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("Musisz być w kanale głosowym!")
            return
    music_queue.append(url)
    await ctx.send(f"Dodano do kolejki: {url}")
    if not ctx.voice_client.is_playing():
        play_next(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Pominąłem piosenkę.")
    else:
        await ctx.send("Nie ma nic do pominięcia.")

@bot.command()
async def queue(ctx):
    if music_queue:
        msg = "🎵 Kolejka:\n" + "\n".join([f"{i+1}. {url}" for i, url in enumerate(music_queue)])
        await ctx.send(msg)
    else:
        await ctx.send("Kolejka jest pusta.")

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Pauza!")
    else:
        await ctx.send("Nic nie jest odtwarzane.")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Wznawiam!")
    else:
        await ctx.send("Nie ma pauzy.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏹️ Zatrzymano muzykę.")
    else:
        await ctx.send("Bot nie jest w żadnym kanale.")

# ==========================
# AUTOMATYCZNE POWIADOMIENIA TWITCH
# ==========================
@tasks.loop(hours=1)
async def get_twitch_token():
    global TWITCH_TOKEN
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    r = requests.post(url, params=params).json()
    TWITCH_TOKEN = r['access_token']

@tasks.loop(seconds=60)
async def check_stream():
    global IS_LIVE
    if TWITCH_TOKEN is None:
        return
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {TWITCH_TOKEN}"
    }
    url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_CHANNEL}"
    r = requests.get(url, headers=headers).json()
    data = r.get('data')

    channel = discord.utils.get(bot.get_all_channels(), name=DISCORD_CHANNEL_NAME)
    if not channel:
        return

    if data and len(data) > 0:
        if not IS_LIVE:
            await channel.send(f"🔴 {TWITCH_CHANNEL} właśnie wystartował! Dołączcie na stream!")
            IS_LIVE = True
    else:
        IS_LIVE = False

# ==========================
# ODPOWIEDZI NA WIADOMOŚCI
# ==========================
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    msg = message.content.lower()

    if "cześć" in msg or "hej" in msg:
        await message.channel.send(f"Hej {message.author.mention}! 👋")
    elif "jak się masz" in msg:
        await message.channel.send("Dobrze, dzięki że pytasz! 😊")
    elif "dzięki" in msg or "thx" in msg:
        await message.channel.send("Nie ma sprawy! 😎")
    elif "stream" in msg:
        await message.channel.send(f"Nie zapomnijcie odwiedzić {TWITCH_CHANNEL} na Twitchu! 🔴")

    await bot.process_commands(message)

# ==========================
# URUCHOMIENIE BOTA
# ==========================
bot.run(os.getenv("DISCORD_TOKEN"))

