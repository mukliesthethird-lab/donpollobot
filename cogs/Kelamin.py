import discord
from discord.ext import commands

class ReactionRoleSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Laki", value="laki", emoji="🧒🏿"),
            discord.SelectOption(label="Perempuan", value="perempuan", emoji="👩🏻"),
        ]
        super().__init__(placeholder="Pilih Kelaminmu", min_values=1, max_values=1, options=options, custom_id="kelamin_select_menu")

    async def callback(self, interaction: discord.Interaction):
        selected_role_name = self.values[0]
        guild = interaction.guild
        user = interaction.user

        roles_to_check = ["Laki", "Perempuan"]

        for role_name in roles_to_check:
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role in user.roles and role.name.lower() != selected_role_name:
                await user.remove_roles(role)

        selected_role = discord.utils.get(guild.roles, name=selected_role_name.capitalize())
        if selected_role:
            await user.add_roles(selected_role)
            embed = discord.Embed(
                title="Role Diperbarui",
                description=f"Role {selected_role.mention} telah ditambahkan ke {user.mention}.",
                color=discord.Color.from_rgb(43, 45, 49),
            )
            embed.set_thumbnail(url=user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="Error",
                description=f"Role {selected_role.mention} telah ditambahkan ke {user.mention}.",
                color=discord.Color.from_rgb(43, 45, 49),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ReactionRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  
        self.add_item(ReactionRoleSelect())

class ReactionRoleCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.client.add_view(ReactionRoleView()) 

    @commands.Cog.listener()
    async def on_ready(self):
        print('Kelamin Role Cog is ready')

    @commands.command()
    async def kelamin(self, ctx):
        embed = discord.Embed(
            title="Tentukan Kelaminmu",
            description=(
                "> <@&1268794897289449503>\n"
                "> <@&1268794932043452502>\n"
            ),
            color=discord.Color.from_rgb(43, 45, 49),
        )
        embed.set_image(url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWE2N2RiN2MwOWJlNmQ3ODc4MGIwYzE5YTkzOTAwYzI4NTEwNWE1YSZjdD1n/vKQnIaSHRHouihBWFO/giphy-downsized-large.gif")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1092648085647269963/1092839604257837076/Untitled.jpg?width=524&height=700&ex=66ada9f1&is=66ac5871&hm=ad70dd2cd39d6f1cb1510203274c81098b2be1526a762f8d009dbf2d8d73f7d9&")

        await ctx.send(embed=embed, view=ReactionRoleView())

async def setup(client):
    await client.add_cog(ReactionRoleCog(client))

# Maintenance update
