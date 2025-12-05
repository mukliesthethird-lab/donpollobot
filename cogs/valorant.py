import discord
from discord.ext import commands
from discord import app_commands
from utils.riot_api import get_valorant_stats
import asyncio

class ValorantStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="valorant",
        description="Cek stats VALORANT pemain berdasarkan Riot ID (tanpa perlu region)"
    )
    @app_commands.describe(
        username="Username Riot (contoh: Example#1234)"
    )
    async def valorant_stats(
        self, 
        interaction: discord.Interaction, 
        username: str
    ):
        """Command utama untuk mengecek stats VALORANT"""
        await interaction.response.defer()
        
        try:
            if '#' not in username:
                return await interaction.followup.send(
                    "Format username salah! Gunakan format: NamaUser#Tagline"
                )
            
            name, tag = username.split('#', 1)
            stats = await get_valorant_stats(name, tag)  # Tanpa region
            
            if not stats:
                return await interaction.followup.send(
                    "Pemain tidak ditemukan atau terjadi error!"
                )
            
            embed = self._create_stats_embed(username, stats)
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error: {e}")
            await interaction.followup.send(
                "Terjadi error saat mengambil data stats!"
            )

    @app_commands.command(
        name="valorant_dummy",
        description="Cek tampilan stats VALORANT (Data Palsu/Dummy)"
    )
    async def valorant_dummy(self, interaction: discord.Interaction):
        """Command dummy untuk testing UI"""
        await interaction.response.defer()
        
        # Import di sini untuk menghindari circular import jika ada, 
        # tapi karena utils terpisah aman.
        from utils.riot_api import get_mock_stats
        
        stats = await get_mock_stats()
        embed = self._create_stats_embed("DummyUser#TEST", stats)
        
        await interaction.followup.send(
            content="⚠️ **Note:** Ini adalah data dummy untuk testing.",
            embed=embed
        )

    def _create_stats_embed(self, username: str, stats: dict) -> discord.Embed:
        """Membuat embed untuk menampilkan stats"""
        embed = discord.Embed(
            title=f"VALORANT Stats untuk {username}",
            color=0xfa4454  # Warna merah VALORANT
        )
        
        embed.add_field(name="🏆 Rank", value=stats.get('current_rank', 'Unknown'), inline=True)
        embed.add_field(name="📈 Peak Rank", value=stats.get('peak_rank', 'Unknown'), inline=True)
        embed.add_field(name="📊 Win Rate", value=stats.get('win_rate', 'Unknown'), inline=True)
        
        embed.add_field(name="🔫 K/D Ratio", value=stats.get('kd_ratio', 'Unknown'), inline=True)
        if 'headshot_percent' in stats:
            embed.add_field(name="🎯 Headshot %", value=stats['headshot_percent'], inline=True)
        
        # Spacer
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        if 'top_agents' in stats and stats['top_agents']:
            embed.add_field(
                name="🕵️ Top Agents", 
                value="\n".join(stats['top_agents']),
                inline=True
            )

        if 'top_weapon' in stats and stats['top_weapon']:
            weapon = stats['top_weapon']
            embed.add_field(
                name="🔫 Top Weapon",
                value=f"{weapon['name']}\n{weapon['kills']} Kills",
                inline=True
            )
            # Set thumbnail to weapon if available, otherwise rank
            if weapon.get('image'):
                embed.set_thumbnail(url=weapon['image'])

        if 'top_map' in stats and stats['top_map']:
            tmap = stats['top_map']
            embed.add_field(
                name="🗺️ Top Map",
                value=f"{tmap['name']}\n{tmap['win_rate']} Win Rate",
                inline=True
            )

        embed.set_footer(text=f"Level {stats.get('account_level', 'Unknown')} • Stats diperbarui")
        
        # If we didn't use weapon image as thumbnail, use rank image
        if 'rank_image' in stats and not embed.thumbnail:
            embed.set_thumbnail(url=stats['rank_image'])
        elif 'rank_image' in stats:
             # If thumbnail is taken (by weapon), put rank in author icon or similar if desired
             # But let's just keep rank image as the main thumbnail if weapon image is missing
             # Or maybe put rank image in the author icon?
             embed.set_author(name=f"Stats for {username}", icon_url=stats['rank_image'])
             
        if not embed.author:
             embed.set_author(name=f"Stats for {username}")

        return embed

async def setup(bot: commands.Bot):
    await bot.add_cog(ValorantStats(bot))
