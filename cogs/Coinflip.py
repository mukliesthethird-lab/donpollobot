import discord
from discord import app_commands
from discord.ext import commands
import random

HEADS_IMAGE_URL = 'https://i.imgur.com/dolsgRC.png'
TAILS_IMAGE_URL = 'https://i.imgur.com/wFwdoSw.png'

class Coinflip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Coinflip Cog is ready')

    # Slash command: /coinflip
    @app_commands.command(name="coinflip", description="Lempar koin dan lihat hasilnya (Garuda atau Rupiah)")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Garuda", "Rupiah"])
        image_url = HEADS_IMAGE_URL if result == "Garuda" else TAILS_IMAGE_URL

        embed = discord.Embed(
            title="Coin Flip",
            description=f"{interaction.user.mention} melempar koin!",
            color=discord.Color.from_rgb(43, 45, 49),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.add_field(name="Hasilnya", value=result, inline=False)
        embed.set_image(url=image_url)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Coinflip(bot))

# Maintenance update
