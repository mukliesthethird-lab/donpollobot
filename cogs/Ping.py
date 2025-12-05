import discord
from discord.ext import commands
from discord import app_commands

class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Ping Cog is ready')

    @app_commands.command(name="ping", description="Melihat latency bot")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)

        if latency < 100:
            color = discord.Color.green()
        elif latency < 300:
            color = discord.Color.orange()
        else:
            color = discord.Color.red()

        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: {latency}ms",
            color=color
        )
        embed.set_footer(text=f"Diminta oleh {interaction.user}", icon_url=interaction.user.avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))

# Maintenance update
