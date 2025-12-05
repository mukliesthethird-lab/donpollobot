import discord
from discord.ext import commands
from discord import app_commands
import random

class GuessNumber(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ GuessNumber Cog is ready')

    @app_commands.command(name="tebakangka", description="Tebak angka dari 1 sampai 100!")
    async def tebakangka(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(
            title="Tebak Angka",
            description="Saya sudah memilih angka dari 1-100. Silakan tebak!",
            color=discord.Color.blue()
        ))

        target_number = random.randint(1, 100)
        attempts = 0

        def check(msg):
            return msg.author.id == interaction.user.id and msg.channel == interaction.channel

        while attempts < 10:
            try:
                msg = await self.client.wait_for('message', check=check, timeout=30.0)
                guess = int(msg.content)
            except ValueError:
                await interaction.followup.send(embed=discord.Embed(
                    title="Input Salah",
                    description="Masukin angka, bukan huruf!",
                    color=discord.Color.red()
                ))
                continue
            except Exception:
                await interaction.followup.send(embed=discord.Embed(
                    title="Waktu Habis",
                    description="Waktu habis. Coba lagi nanti.",
                    color=discord.Color.red()
                ))
                return

            attempts += 1

            if guess < target_number:
                await interaction.followup.send(embed=discord.Embed(
                    title="Tebakan Rendah",
                    description="Terlalu kecil! Coba lagi.",
                    color=discord.Color.orange()
                ))
            elif guess > target_number:
                await interaction.followup.send(embed=discord.Embed(
                    title="Tebakan Tinggi",
                    description="Terlalu besar! Coba lagi.",
                    color=discord.Color.orange()
                ))
            else:
                await interaction.followup.send(embed=discord.Embed(
                    title="Benar!",
                    description=f"Nice! Angkanya adalah {target_number}. Kamu menebak dalam {attempts} kali.",
                    color=discord.Color.green()
                ))
                break

async def setup(client):
    await client.add_cog(GuessNumber(client))

# Maintenance update
