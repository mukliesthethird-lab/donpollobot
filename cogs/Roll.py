import discord
from discord import app_commands
from discord.ext import commands
import random

class Rolls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Roll Cog is ready')

    @app_commands.command(name="roll", description="Roll angka acak antara 0 sampai nilai maksimum (default: 100)")
    @app_commands.describe(max_value="Nilai maksimum roll (antara 1-100)")
    async def roll(self, interaction: discord.Interaction, max_value: int = 100):
        if max_value < 1 or max_value > 100:
            await interaction.response.send_message("Silakan masukkan angka antara 1 dan 100.", ephemeral=True)
            return

        roll = random.randint(0, max_value)
        roll_formatted = f"{roll:03}"
        max_value_formatted = f"{max_value:03}"

        embed = discord.Embed(
            title="Roll Result",
            description=f"{interaction.user.mention} mendapatkan `{roll_formatted}/{max_value_formatted}`",
            color=discord.Color.from_rgb(43, 45, 49),
        )
        embed.set_footer(text=f"Diminta oleh {interaction.user}", icon_url=interaction.user.avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Rolls(bot))

# Maintenance update
