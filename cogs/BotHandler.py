import discord
from discord.ext import commands
import json
import traceback
# Try importing aiomysql, warn if missing
try:
    import aiomysql
except ImportError:
    aiomysql = None
    print("❌ [BotHandler] CRITICAL: 'aiomysql' library not found. Please run 'pip install aiomysql'")
# --- DATABASE CONFIG (FALLBACK) ---
# Used because self.bot.pool is missing
DB_CONFIG = {
    'host': 'ar-men-08.vexyhost.com',
    'user': 'u8459_duPcRgL0yL',
    'password': '7J5ut2hbR!Wkbxb6nnB!+xsk',
    'db': 's8459_database',
    'port': 3306,
    'autocommit': True
}
class BotHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.local_pool = None
    async def get_db_pool(self):
        # 1. Try to find global pool (unlikely based on logs, but good practice)
        pool = (getattr(self.bot, 'pool', None) or 
                getattr(self.bot, 'db_pool', None) or 
                getattr(self.bot, 'db', None) or 
                getattr(self.bot, 'database', None))
        
        if pool:
            return pool
            
        # 2. Fallback: Create local pool if not exists
        if not self.local_pool:
            if not aiomysql:
                print("❌ [BotHandler] Cannot create fallback connection: aiomysql not installed.")
                return None
            try:
                print(f"[BotHandler] Attempting fallback connection to {DB_CONFIG['host']}...")
                self.local_pool = await aiomysql.create_pool(**DB_CONFIG)
                print("[BotHandler] ✅ Fallback DB connection established successfully!")
            except Exception as e:
                print(f"❌ [BotHandler] Failed to create local DB pool: {e}")
                traceback.print_exc()
        
        return self.local_pool
    async def safe_respond(self, interaction: discord.Interaction, message: str, ephemeral: bool = True):
        """Safely respond to an interaction, handling race conditions."""
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(message, ephemeral=ephemeral)
            else:
                await interaction.followup.send(message, ephemeral=ephemeral)
        except discord.errors.InteractionResponded:
            try:
                await interaction.followup.send(message, ephemeral=ephemeral)
            except Exception:
                pass
        except Exception as e:
            print(f"[BotHandler] Failed to respond: {e}")
    async def get_component_rows(self, message_id):
        pool = await self.get_db_pool()
        
        if not pool:
            print("❌ [BotHandler] No valid database connection available.")
            return None
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT component_rows FROM reaction_role_messages WHERE message_id = %s", (message_id,))
                result = await cursor.fetchone()
                
                if not result:
                    return None
                
                # Handle Dict or Tuple
                if hasattr(result, 'get'):
                    return result.get('component_rows')
                else:
                    return result[0]
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get('custom_id')
        if not custom_id:
            return
        # Debug print
        print(f"[BotHandler] Interaction: {custom_id}")
        try:
            # 1. Fetch Config
            component_rows_raw = await self.get_component_rows(str(interaction.message.id))
            
            if not component_rows_raw:
                print(f"[BotHandler] Message {interaction.message.id} not found in DB. Ignoring.")
                return
            if isinstance(component_rows_raw, str):
                component_rows = json.loads(component_rows_raw)
            else:
                component_rows = component_rows_raw or []
            matched_component = None
            matched_actions = []
            # 2. Find Component
            for row in component_rows:
                for comp in row:
                    if comp.get('custom_id') == custom_id:
                        matched_component = comp
                        matched_actions = list(comp.get('actions', []))
                        if comp.get('type') == 3: # Select Menu
                            selected_values = interaction.data.get('values', [])
                            if 'options' in comp:
                                for opt in comp['options']:
                                    if opt['value'] in selected_values:
                                        matched_actions.extend(opt.get('actions', []))
                        break
                if matched_component:
                    break
            if not matched_component or not matched_actions:
                await self.safe_respond(interaction, "❌ No actions configured.")
                return
            # Defer the response for longer operations
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=True)
            except discord.errors.InteractionResponded:
                pass  # Already responded, continue with followup
            # 3. Execute Actions
            success_msgs = []
            failure_msgs = []
            for action in matched_actions:
                action_type = action.get('type')
                print(f"[BotHandler] Executing: {action_type}")
                
                try:
                    if action_type == 'add_role':
                        role_id = int(action.get('role_id'))
                        role = interaction.guild.get_role(role_id)
                        if role:
                            await interaction.user.add_roles(role)
                            success_msgs.append(action.get('success_message') or f"✅ Added role **{role.name}**")
                        else:
                            failure_msgs.append(action.get('failure_message') or "❌ Role not found")
                    elif action_type == 'remove_role':
                        role_id = int(action.get('role_id'))
                        role = interaction.guild.get_role(role_id)
                        if role:
                            await interaction.user.remove_roles(role)
                            success_msgs.append(action.get('success_message') or f"✅ Removed role **{role.name}**")
                        else:
                            failure_msgs.append(action.get('failure_message') or "❌ Role not found")
                    elif action_type == 'toggle_role':
                        role_id = int(action.get('role_id'))
                        role = interaction.guild.get_role(role_id)
                        if role:
                            if role in interaction.user.roles:
                                await interaction.user.remove_roles(role)
                                success_msgs.append(action.get('success_message') or f"✅ Removed role **{role.name}**")
                            else:
                                await interaction.user.add_roles(role)
                                success_msgs.append(action.get('success_message') or f"✅ Added role **{role.name}**")
                        else:
                            failure_msgs.append(action.get('failure_message') or "❌ Role not found")
                    elif action_type == 'send_message':
                        content = action.get('message_content', '')
                        await interaction.followup.send(content, ephemeral=True)
                        if action.get('success_message'): success_msgs.append(action.get('success_message'))
                    elif action_type == 'dm_user':
                        content = action.get('message_content', '')
                        try:
                            await interaction.user.send(content)
                            success_msgs.append(action.get('success_message') or "✅ Sent you a DM")
                        except discord.Forbidden:
                            failure_msgs.append(action.get('failure_message') or "❌ Cannot DM you (Privacy Settings)")
                    elif action_type == 'send_message_channel':
                        channel_id = int(action.get('target_channel_id'))
                        channel = interaction.guild.get_channel(channel_id)
                        content = action.get('message_content', '')
                        if channel:
                            await channel.send(content)
                            success_msgs.append(action.get('success_message') or f"✅ Message sent to {channel.mention}")
                        else:
                            failure_msgs.append(action.get('failure_message') or "❌ Target channel not found")
                    
                    elif action_type == 'move_voice':
                        channel_id = int(action.get('target_channel_id'))
                        channel = interaction.guild.get_channel(channel_id)
                        if channel and interaction.user.voice:
                            await interaction.user.move_to(channel)
                            success_msgs.append(action.get('success_message') or f"✅ Moved to {channel.name}")
                        else:
                            failure_msgs.append(action.get('failure_message') or "❌ User not in voice or channel invalid")
                except Exception as e:
                    print(f"Error executing action {action_type}: {e}")
                    traceback.print_exc()
                    failure_msgs.append(action.get('failure_message') or "❌ Error executing action")
            # 4. Final Response
            success_msgs = [m for m in success_msgs if m]
            failure_msgs = [m for m in failure_msgs if m]
            
            final_response = ""
            if success_msgs: final_response += "\n".join(success_msgs)
            if failure_msgs:
                if final_response: final_response += "\n\n"
                final_response += "\n".join(failure_msgs)
            if final_response:
                try:
                    await interaction.followup.send(final_response, ephemeral=True)
                except Exception as e:
                    print(f"[BotHandler] Failed to send final response: {e}")
        except Exception as e:
            print(f"Interaction Handler Error: {e}")
            traceback.print_exc()
            await self.safe_respond(interaction, "❌ System Error (Check Bot Console)")
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[BotHandler] ✅ Ready! Logged in as {self.bot.user}")
async def setup(bot):
    await bot.add_cog(BotHandler(bot))