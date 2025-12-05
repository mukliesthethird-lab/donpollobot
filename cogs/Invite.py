import discord
from discord import app_commands
from discord.ext import commands

class Invite(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Invite Slash Command Cog Loaded')

    @app_commands.command(name="invite", description="Mengirimkan link undangan bot ke DM Anda")
    async def invite(self, interaction: discord.Interaction):
        invite_link = 'https://discord.com/oauth2/authorize?client_id=1257064052203458712&scope=bot%20applications.commands&permissions=8'
        embed = discord.Embed(
            title="Link Undangan Bot",
            description=f"Link undangan bot [Klik di sini]({invite_link})",
            color=discord.Color.from_rgb(43, 45, 49),
        )

        try:
            await interaction.user.send(embed=embed)
            success_embed = discord.Embed(
                title="Sukses ✅",
                description="Link undangan bot telah dikirimkan ke DM Anda!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=success_embed, ephemeral=True)
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="Error ⚠️",
                description="Saya tidak bisa mengirimkan DM ke Anda. Pastikan pengaturan privasi Anda mengizinkan DM dari server ini.",
                color=discord.Color.red()
            )
            error_embed.set_footer(text=f"Diminta oleh {interaction.user}", icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

async def setup(client: commands.Bot):
    await client.add_cog(Invite(client))

# Maintenance update
