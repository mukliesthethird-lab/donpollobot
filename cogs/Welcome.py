import discord
from discord.ext import commands
import json
import re
from datetime import datetime
from utils.database import get_db_connection



class Welcome(commands.Cog):
    """Handles welcome, leave, boost, and role assignment messages"""
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Welcome Cog is ready')


    def get_settings(self, guild_id: int) -> dict | None:
        """Get welcome settings from database"""
        try:
            conn = get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM welcome_settings WHERE guild_id = %s",
                (str(guild_id),)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row and row.get('embed_data'):
                try:
                    embed_data = json.loads(row['embed_data']) if isinstance(row['embed_data'], str) else row['embed_data']
                    return embed_data
                except json.JSONDecodeError:
                    return None
            return None
        except Exception as e:
            print(f"[Welcome] Error getting settings: {e}")
            return None

    def parse_variables(self, text: str, member: discord.Member, role: discord.Role = None) -> str:
        """Replace variables in text with actual values"""
        if not text:
            return text
        
        replacements = {
            '{user}': member.mention,
            '{user.name}': member.display_name,
            '{user.avatar}': str(member.display_avatar.url),
            '{server}': member.guild.name,
            '{server.members}': f"{member.guild.member_count:,}",
            '{date}': datetime.now().strftime("%d/%m/%Y"),
        }
        
        if role:
            replacements['{role}'] = role.name
        
        for var, value in replacements.items():
            text = text.replace(var, value)
        
        return text

    def build_embeds(self, config: dict, member: discord.Member, role: discord.Role = None) -> list[discord.Embed]:
        """Build Discord embeds from config"""
        embeds = []
        
        for embed_data in config.get('embeds', []):
            # Parse color
            color_str = embed_data.get('color', '#FFD700')
            try:
                color = int(color_str.lstrip('#'), 16)
            except:
                color = 0xFFD700
            
            embed = discord.Embed(color=color)
            
            # Title
            if embed_data.get('title'):
                embed.title = self.parse_variables(embed_data['title'], member, role)
            
            # Description
            if embed_data.get('description'):
                embed.description = self.parse_variables(embed_data['description'], member, role)
            
            # Author
            if embed_data.get('author_name'):
                author_icon = self.parse_variables(embed_data.get('author_icon_url', ''), member, role)
                embed.set_author(
                    name=self.parse_variables(embed_data['author_name'], member, role),
                    icon_url=author_icon if author_icon.startswith('http') else None
                )
            
            # Thumbnail
            if embed_data.get('thumbnail_url'):
                thumbnail = self.parse_variables(embed_data['thumbnail_url'], member, role)
                if thumbnail.startswith('http'):
                    embed.set_thumbnail(url=thumbnail)
            
            # Image
            if embed_data.get('image_url'):
                image = self.parse_variables(embed_data['image_url'], member, role)
                if image.startswith('http'):
                    embed.set_image(url=image)
            
            # Footer
            if embed_data.get('footer_text'):
                footer_icon = self.parse_variables(embed_data.get('footer_icon_url', ''), member, role)
                embed.set_footer(
                    text=self.parse_variables(embed_data['footer_text'], member, role),
                    icon_url=footer_icon if footer_icon.startswith('http') else None
                )
            
            # Fields
            for field in embed_data.get('fields', []):
                if field.get('name') and field.get('value'):
                    embed.add_field(
                        name=self.parse_variables(field['name'], member, role),
                        value=self.parse_variables(field['value'], member, role),
                        inline=field.get('inline', False)
                    )
            
            embeds.append(embed)
        
        return embeds

    def build_view(self, config: dict) -> discord.ui.View | None:
        """Build button view from action_rows config"""
        action_rows = config.get('action_rows', [])
        if not action_rows:
            return None
        
        view = discord.ui.View(timeout=None)
        
        for row in action_rows:
            for button in row:
                if button.get('url'):
                    btn = discord.ui.Button(
                        label=button.get('label', 'Link'),
                        url=button['url'],
                        emoji=button.get('emoji') or None,
                        style=discord.ButtonStyle.link
                    )
                    view.add_item(btn)
        
        return view if len(view.children) > 0 else None

    async def send_message(self, config: dict, member: discord.Member, role: discord.Role = None):
        """Send welcome/leave/boost/role message to configured channel"""
        if not config.get('enabled'):
            return
        
        channel_id = config.get('channel_id')
        if not channel_id:
            return
        
        channel = member.guild.get_channel(int(channel_id))
        if not channel:
            return
        
        # Build message content
        content = None
        if config.get('message_content'):
            content = self.parse_variables(config['message_content'], member, role)
        
        # Build embeds
        embeds = self.build_embeds(config, member, role)
        
        # Build view (buttons)
        view = self.build_view(config)
        
        try:
            await channel.send(content=content, embeds=embeds, view=view)
        except discord.Forbidden:
            print(f"[Welcome] No permission to send to channel {channel_id}")
        except Exception as e:
            print(f"[Welcome] Error sending message: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle member join event"""
        settings = self.get_settings(member.guild.id)
        if not settings:
            return
        
        join_config = settings.get('join')
        if join_config:
            await self.send_message(join_config, member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Handle member leave event"""
        settings = self.get_settings(member.guild.id)
        if not settings:
            return
        
        leave_config = settings.get('leave')
        if leave_config:
            await self.send_message(leave_config, member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Handle role changes and boost events"""
        settings = self.get_settings(after.guild.id)
        if not settings:
            return
        
        # Check for boost
        if before.premium_since is None and after.premium_since is not None:
            boost_config = settings.get('boost')
            if boost_config:
                await self.send_message(boost_config, after)
        
        # Check for role changes
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        
        added_roles = after_roles - before_roles
        removed_roles = before_roles - after_roles
        
        role_config = settings.get('role')
        if not role_config or not role_config.get('enabled'):
            return
        
        tracked_roles = role_config.get('tracked_roles', [])
        announce_type = role_config.get('announce_type', 'both')
        
        # Handle added roles
        if announce_type in ('both', 'add'):
            for role in added_roles:
                # Skip if tracked_roles is set and this role is not in it
                if tracked_roles and str(role.id) not in tracked_roles:
                    continue
                await self.send_message(role_config, after, role)
        
        # Handle removed roles
        if announce_type in ('both', 'remove'):
            for role in removed_roles:
                if tracked_roles and str(role.id) not in tracked_roles:
                    continue
                # Modify config temporarily for removed message
                removed_config = {**role_config}
                if removed_config.get('embeds'):
                    for embed in removed_config['embeds']:
                        if '{role}' in embed.get('description', ''):
                            # Change message for removal
                            embed['description'] = embed['description'].replace(
                                'now has the **{role}** role',
                                'no longer has the **{role}** role'
                            )
                await self.send_message(removed_config, after, role)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
