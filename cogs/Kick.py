import discord
from discord import app_commands
from discord.ext import commands

USAGE_IMAGE_URL = 'https://i.imgur.com/AWtQELc.png'

class Kick(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Kick Cog is ready')

    @app_commands.command(name="kick", description="Menendang anggota dari server")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = None
    ):
        if not interaction.user.guild_permissions.kick_members:
            embed = discord.Embed(
                title="Kick Command",
                description="Maaf, Anda tidak memiliki izin untuk menendang anggota.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if member is None:
            embed = discord.Embed(
                title="Penggunaan Command Salah",
                description="Cara menggunakan command ini: `/kick <anggota> [alasan]`.\n\nContoh: `/kick @User Spamming` untuk menendang anggota dengan alasan spamming.",
                color=discord.Color.red()
            )
            embed.set_image(url=USAGE_IMAGE_URL)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="Member Kicked",
                description=f'{member.mention} telah ditendang!',
                color=discord.Color.from_rgb(43, 45, 49),
            )
            if reason:
                embed.add_field(name="Alasan", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            embed = discord.Embed(
                title="Error",
                description="Bot tidak memiliki izin untuk menendang anggota ini.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"Terjadi kesalahan: {str(e)}",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Kick(bot))

# Maintenance update
