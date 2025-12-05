import discord
from discord.ext import commands
from discord import app_commands

class Userinfo(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Userinfo Cog is ready')

    @app_commands.command(name="userinfo", description="Menampilkan informasi pengguna")
    @app_commands.describe(member="Pilih pengguna yang ingin ditampilkan informasinya")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user

        embed = discord.Embed(
            title=f"Informasi Pengguna : {member.name}",
            color=discord.Color.from_rgb(43, 45, 49),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="__ID__", value=member.id, inline=True)
        embed.add_field(name="__Nama__", value=member.name, inline=True)
        embed.add_field(name="__Status__", value=member.status.name if hasattr(member, "status") else "Unknown", inline=True)
        embed.add_field(name="__Tanggal Registrasi__", value=member.created_at.strftime("%a, %B %#d, %Y, %I:%M %p"), inline=False)
        embed.add_field(name="__Tanggal Bergabung__", value=member.joined_at.strftime("%a, %B %#d, %Y, %I:%M %p"), inline=False)
        embed.add_field(
            name=f"__Roles({len(member.roles)})__",
            value=" ".join([role.mention for role in member.roles if role.name != "@everyone"]),
            inline=False
        )
        embed.set_footer(text=f"Diminta oleh {interaction.user}", icon_url=interaction.user.avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(client: commands.Bot):
    await client.add_cog(Userinfo(client))

# Maintenance update
