import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime

# Load bot token from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# ---- Customizable Bot Presence Configuration ----

STATUS = discord.Status.idle  # Options: online, idle, dnd, invisible, offline

ACTIVITY_TYPE = discord.ActivityType.playing  # Options: playing, streaming, listening, watching, competing

ACTIVITY_TEXT = "Custom RP Experience"

ACTIVITY_IMAGE = "https://i.imgur.com/xyz.png"  # Use for rich presence (streaming or timestamp activities)

USE_TIMESTAMP = True  # Enable timestamp (e.g., when started playing/watching etc.)

# --------------------------------------------------

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    if USE_TIMESTAMP:
        activity = discord.Activity(
            type=ACTIVITY_TYPE,
            name=ACTIVITY_TEXT,
            start=datetime.utcnow(),
            assets=discord.ActivityAssets(large_image=ACTIVITY_IMAGE) if ACTIVITY_IMAGE else None
        )
    else:
        if ACTIVITY_TYPE == discord.ActivityType.streaming:
            activity = discord.Streaming(name=ACTIVITY_TEXT, url="https://twitch.tv/yourchannel")
        else:
            activity = discord.Activity(type=ACTIVITY_TYPE, name=ACTIVITY_TEXT)

    await bot.change_presence(status=STATUS, activity=activity)
    print(f"{bot.user} is now online with custom presence.")

bot.run(TOKEN)
