import discord
from discord.ext import commands
import os   # <- bardzo ważne! dzięki temu os.getenv działa

# Ustawienie intencji (potrzebne, żeby bot czytał wiadomości)
intents = discord.Intents.default()
intents.message_content = True

# Prefix komend np. !hej
bot = commands.Bot(command_prefix="!", intents=intents)

# Event uruchomienia bota
@bot.event
async def on_ready():
    print(f"Bot zalogowany jako {bot.user}")

# Przykładowa komenda !hej
@bot.command()
async def hej(ctx):
    await ctx.send("Hej! 👋 Miło Cię widzieć!")

# Przykładowa komenda !ping
@bot.command()
async def ping(ctx):
    await ctx.send("Pong 🏓")

# Uruchomienie bota – token pobierany z Railway jako zmienna środowiskowa
bot.run(os.getenv("DISCORD_TOKEN"))

