import discord
from discord import app_commands
from discord.ext import commands
import asyncio

USAGE_IMAGE_URL = 'https://i.imgur.com/AWtQELc.png'

class Reminder(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Reminder Cog is ready.')

    @app_commands.command(name="remind", description="Membuat pengingat setelah beberapa menit.")
    @app_commands.describe(time="Jumlah menit sebelum pengingat dikirim", reminder="Isi pengingat")
    async def remind(self, interaction: discord.Interaction, time: int, reminder: str):
        if time <= 0:
            embed_error = discord.Embed(
                title="Penggunaan Command Salah",
                description="Masukkan angka menit yang lebih dari 0.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return

        embed_initial = discord.Embed(
            title="✅ Pengingat Ditambahkan",
            description=f"Saya akan mengingatkan Anda tentang `{reminder}` dalam {time} menit.",
            color=discord.Color.from_rgb(43, 45, 49),
        )

        await interaction.response.send_message(embed=embed_initial)

        await asyncio.sleep(time * 60)

        embed_reminder = discord.Embed(
            title="Pengingat",
            description=f"⚠️ {interaction.user.mention}, ini pengingat Anda: `{reminder}`",
            color=discord.Color.from_rgb(43, 45, 49),
        )

        await interaction.channel.send(embed=embed_reminder)

async def setup(client: commands.Bot):
    await client.add_cog(Reminder(client))

# Maintenance update
