import discord
from discord import app_commands
from discord.ext import commands

USAGE_IMAGE_URL = 'https://i.imgur.com/AWtQELc.png'

class Purge(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Purge Cog is ready')

    @app_commands.command(name="purge", description="Hapus sejumlah pesan dari channel.")
    @app_commands.describe(amount="Jumlah pesan yang akan dihapus (maks 100)")
    async def purge(self, interaction: discord.Interaction, amount: int):
        if not interaction.user.guild_permissions.manage_messages:
            embed = discord.Embed(
                title="Purge Command",
                description="Maaf, Anda tidak memiliki izin untuk menghapus pesan.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if amount <= 0:
            embed = discord.Embed(
                title="Purge Command",
                description="Masukkan angka di atas 0.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if amount > 100:
            amount = 100

        deleted = await interaction.channel.purge(limit=amount)
        emoji = '<a:sip:1267438889522561065>'
        embed = discord.Embed(
            title=f"{emoji} Berhasil",
            description=f"{len(deleted)} pesan terhapus.",
            color=discord.Color.from_rgb(43, 45, 49),
        )
        embed.set_footer(text=f"Diminta oleh {interaction.user}", icon_url=interaction.user.avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(client):
    await client.add_cog(Purge(client))

# Maintenance update
