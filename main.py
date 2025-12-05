import discord
from discord.ext import commands
import os
import asyncio
import traceback
from dotenv import load_dotenv
#
load_dotenv()

# Gunakan intents yang dibutuhkan
intents = discord.Intents.default()
intents.message_content = True 
intents.guilds = True 
intents.members = True 

# Buat bot instance DENGAN prefix, agar !reload bisa berfungsi
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    
    # Sync commands globally on startup
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Synced {len(synced)} commands globally")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    activity = discord.Activity(type=discord.ActivityType.listening, name='/help')
    await bot.change_presence(activity=activity)

# Load semua cogs
async def load_cogs():
    for root, _, files in os.walk("./cogs"):
        for filename in files:
            if filename.endswith(".py") and filename != "__init__.py":
                relative = os.path.relpath(os.path.join(root, filename), "./cogs")
                module = "cogs." + relative.replace(os.sep, ".")[:-3]
                try:
                    await bot.load_extension(module)
                    print(f"🔃 Loaded {module}")
                except Exception as e:
                    print(f"❌ Gagal load {module}: {e}")
                    traceback.print_exc()

# Jalankan bot
async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")

    if TOKEN is None:
        print("❌ ERROR: Token tidak ditemukan di file .env!")
        return

    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
