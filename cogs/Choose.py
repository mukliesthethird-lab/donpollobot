import discord
from discord import app_commands
from discord.ext import commands
import random

USAGE_IMAGE_URL = 'https://i.imgur.com/AWtQELc.png'

class Choose(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Choose Cog is ready')

    # Slash command: /choose <pilihan>
    @app_commands.command(name="choose", description="Pilih satu dari beberapa opsi yang kamu berikan")
    @app_commands.describe(
        options="Masukkan pilihan dipisahkan dengan spasi atau koma, contoh: Apel Pisang Jeruk"
    )
    async def choose(self, interaction: discord.Interaction, options: str):
        # Pisahkan input menjadi list pilihan
        # Bisa pakai koma atau spasi
        if "," in options:
            choices = [opt.strip() for opt in options.split(",") if opt.strip()]
        else:
            choices = options.split()

        if not choices or len(choices) < 2:
            embed = discord.Embed(
                title="Penggunaan Command Salah",
                description=(
                    "Masukkan minimal dua pilihan.\n\n"
                    "Contoh: `/choose Apel Pisang Jeruk` atau `/choose Apel, Pisang, Jeruk`"
                ),
                color=discord.Color.red()
            )
            embed.set_image(url=USAGE_IMAGE_URL)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        chosen = random.choice(choices)
        embed = discord.Embed(
            title="Pilihan Telah Dibuat",
            description=f"Saya memilih: **{chosen}**",
            color=discord.Color.from_rgb(43, 45, 49)
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Choose(bot))

# Maintenance update
