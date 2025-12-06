import discord
from discord.ext import commands
import json
import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

class RoleButtons(commands.Cog):
    """Handles role assignment buttons and select menus from dashboard"""
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("RoleButtons cog loaded!")

    def __init__(self, bot):
        self.bot = bot
        self.pool = None
        
    async def get_pool(self):
        """Get or create database connection pool"""
        if self.pool is None:
            self.pool = await aiomysql.create_pool(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 3306)),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                db=os.getenv('DB_NAME', 'donpollobot'),
                autocommit=True
            )
        return self.pool
    
    async def find_component_action(self, guild_id: int, custom_id: str):
        """Find component action from database by custom_id"""
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT component_rows FROM reaction_role_messages WHERE guild_id = %s",
                        (str(guild_id),)
                    )
                    rows = await cur.fetchall()
                    
                    for row in rows:
                        if row['component_rows']:
                            component_rows = json.loads(row['component_rows'])
                            for comp_row in component_rows:
                                for comp in comp_row:
                                    if comp.get('custom_id') == custom_id:
                                        return {
                                            'type': 'button',
                                            'action_type': comp.get('action_type'),
                                            'role_id': comp.get('role_id'),
                                            'component': comp
                                        }
                                    # Check select menu options
                                    if comp.get('type') == 3 and comp.get('options'):
                                        for opt in comp.get('options', []):
                                            if opt.get('value') == custom_id or comp.get('custom_id') == custom_id:
                                                return {
                                                    'type': 'select_menu',
                                                    'options': comp.get('options', []),
                                                    'custom_id': comp.get('custom_id'),
                                                    'component': comp
                                                }
            return None
        except Exception as e:
            print(f"[RoleButtons] Error finding component: {e}")
            return None
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button and select menu interactions"""
        
        # Only handle component interactions
        if interaction.type != discord.InteractionType.component:
            return
            
        custom_id = interaction.data.get('custom_id', '')
        component_type = interaction.data.get('component_type')
        
        # Skip if not from our role system (check custom_id patterns)
        if not custom_id or custom_id.startswith('kelamin_'):
            return
            
        guild = interaction.guild
        user = interaction.user
        
        if not guild or not user:
            return
            
        try:
            # Find component action from database
            action_data = await self.find_component_action(guild.id, custom_id)
            
            if not action_data:
                # Not our component, ignore
                return
            
            # Handle button clicks
            if component_type == 2:  # Button
                action_type = action_data.get('action_type')
                role_id = action_data.get('role_id')
                
                if not action_type or not role_id:
                    # No action configured
                    return
                    
                role = guild.get_role(int(role_id))
                if not role:
                    await interaction.response.send_message(
                        "❌ Role tidak ditemukan!", ephemeral=True
                    )
                    return
                
                await self.execute_role_action(interaction, user, role, action_type)
                
            # Handle select menu selections
            elif component_type == 3:  # Select Menu
                selected_values = interaction.data.get('values', [])
                
                if not selected_values:
                    return
                    
                options = action_data.get('options', [])
                
                # Find matching option and execute action
                for selected_value in selected_values:
                    for opt in options:
                        if opt.get('value') == selected_value:
                            action_type = opt.get('action_type')
                            role_id = opt.get('role_id')
                            
                            if action_type and role_id:
                                role = guild.get_role(int(role_id))
                                if role:
                                    await self.execute_role_action(
                                        interaction, user, role, action_type,
                                        is_select=True, option_label=opt.get('label', 'Option')
                                    )
                                    return
                
        except Exception as e:
            print(f"[RoleButtons] Error handling interaction: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Terjadi kesalahan: {str(e)}", ephemeral=True
                )
    
    async def execute_role_action(self, interaction: discord.Interaction, user: discord.Member, 
                                  role: discord.Role, action_type: str, is_select: bool = False,
                                  option_label: str = None):
        """Execute role action (add, remove, toggle)"""
        
        try:
            if action_type == 'add_role':
                if role in user.roles:
                    await interaction.response.send_message(
                        f"ℹ️ Kamu sudah memiliki role **{role.name}**!",
                        ephemeral=True
                    )
                else:
                    await user.add_roles(role)
                    embed = discord.Embed(
                        title="✅ Role Ditambahkan",
                        description=f"Role {role.mention} telah ditambahkan ke {user.mention}!",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
            elif action_type == 'remove_role':
                if role not in user.roles:
                    await interaction.response.send_message(
                        f"ℹ️ Kamu tidak memiliki role **{role.name}**!",
                        ephemeral=True
                    )
                else:
                    await user.remove_roles(role)
                    embed = discord.Embed(
                        title="❌ Role Dihapus",
                        description=f"Role {role.mention} telah dihapus dari {user.mention}!",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
            elif action_type == 'toggle_role':
                if role in user.roles:
                    await user.remove_roles(role)
                    embed = discord.Embed(
                        title="🔄 Role Di-toggle (Dihapus)",
                        description=f"Role {role.mention} telah dihapus dari {user.mention}!",
                        color=discord.Color.orange()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await user.add_roles(role)
                    embed = discord.Embed(
                        title="🔄 Role Di-toggle (Ditambahkan)",
                        description=f"Role {role.mention} telah ditambahkan ke {user.mention}!",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Unknown action
                pass
                
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Bot tidak memiliki izin untuk mengubah role ini!",
                ephemeral=True
            )
        except Exception as e:
            print(f"[RoleButtons] Error executing role action: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Gagal mengubah role: {str(e)}",
                    ephemeral=True
                )
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        if self.pool:
            self.pool.close()

async def setup(bot):
    await bot.add_cog(RoleButtons(bot))
