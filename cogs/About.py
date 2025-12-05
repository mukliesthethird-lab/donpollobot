import discord
from discord import app_commands
from discord.ext import commands

class About(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ About Cog is ready')

    # Slash Command: /about
    @app_commands.command(name="about", description="Menampilkan informasi tentang bot ini")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Tentang Bot",
            description="Bot ini dibuat karena iseng nontonin Streamer main Dragon Nest",
            color=discord.Color.from_rgb(43, 45, 49),
        )
        embed.add_field(name="Versi", value="1.0.0", inline=True)
        embed.add_field(name="Pembaruan Terakhir", value="1 Juli 2024", inline=True)
        embed.add_field(name="Fitur Utama", value="Moderasi Pesan, Lempar Dadu, Pemungutan Suara, dan lainnya", inline=False)

        avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
        embed.set_footer(text=f"Diminta oleh {interaction.user}", icon_url=avatar_url)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(About(bot))

# Maintenance update
