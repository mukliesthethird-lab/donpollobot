import discord
from discord import app_commands
from discord.ext import commands

class Avatar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Avatar Cog is ready')

    # Slash command: /avatar [user]
    @app_commands.command(name="avatar", description="Menampilkan avatar pengguna")
    @app_commands.describe(user="Pilih pengguna (opsional). Jika kosong, akan menampilkan avatarmu sendiri.")
    async def avatar(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user

        embed = discord.Embed(
            title=f"Avatar dari {user.display_name}",
            color=discord.Color.from_rgb(43, 45, 49),
        )

        embed.set_image(url=user.avatar.url if user.avatar else user.default_avatar.url)
        avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
        embed.set_footer(text=f"Diminta oleh {interaction.user}", icon_url=avatar_url)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Avatar(bot))

# Maintenance update
