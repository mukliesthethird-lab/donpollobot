import discord
from discord.ext import commands
from discord import app_commands

class Serverinfo(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Serverinfo Cog is ready')

    @app_commands.command(name="serverinfo", description="Menampilkan informasi tentang server.")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild

        embed = discord.Embed(
            title=f"Informasi Server: {guild.name}",
            description=f"Berikut adalah informasi terbaru mengenai server **{guild.name}**.",
            color=discord.Color.from_rgb(43, 45, 49),
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        
        # --- PERBAIKAN DI BARIS INI ---
        embed.set_footer(text=f"Diminta oleh {interaction.user}", icon_url=interaction.user.display_avatar.url)

        divider = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        embed.add_field(name="**Nama Server**", value=guild.name, inline=True)
        embed.add_field(name="**ID Server**", value=guild.id, inline=True)
        embed.add_field(name=divider, value="\u200b", inline=False)
        embed.add_field(name="**Pemilik Server**", value=guild.owner.mention, inline=True)
        embed.add_field(name="**Jumlah Anggota**", value=guild.member_count, inline=True)
        embed.add_field(name="**Jumlah Role**", value=len(guild.roles), inline=True)
        embed.add_field(name=divider, value="\u200b", inline=False)
        embed.add_field(name="**Text Channels**", value=len(guild.text_channels), inline=True)
        embed.add_field(name="**Voice Channels**", value=len(guild.voice_channels), inline=True)
        embed.add_field(name="**Total Channels**", value=len(guild.channels), inline=True)
        embed.add_field(name=divider, value="\u200b", inline=False)
        embed.add_field(
            name="**Tanggal Dibuat**", 
            value=guild.created_at.strftime("%A, %d %B %Y, %H:%M WIB"), 
            inline=False
        )

        await interaction.response.send_message(embed=embed)

async def setup(client: commands.Bot):
    await client.add_cog(Serverinfo(client))
# Maintenance update
