import discord
from discord.ext import commands
import json
from datetime import datetime
from utils.database import get_db_connection


class Logging(commands.Cog):
    """Handles server logging for various Discord events"""
    
    def __init__(self, bot):
        self.bot = bot
        self.webhook_cache = {}  # channel_id -> webhook

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Logging Cog is ready')

    def get_settings(self, guild_id: int) -> dict | None:
        """Get logging settings from database"""
        try:
            conn = get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM logging_settings WHERE guild_id = %s",
                (str(guild_id),)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                return {
                    'use_webhooks': bool(row.get('use_webhooks', True)),
                    'ignore_embeds': bool(row.get('ignore_embeds', False)),
                    'ignore_voice_users': bool(row.get('ignore_voice_users', False)),
                    'ignored_channels': json.loads(row.get('ignored_channels', '[]') or '[]'),
                    'ignored_roles': json.loads(row.get('ignored_roles', '[]') or '[]'),
                    'ignored_users': json.loads(row.get('ignored_users', '[]') or '[]'),
                    'category_channels': json.loads(row.get('category_channels', '{}') or '{}'),
                    'type_channels': json.loads(row.get('type_channels', '{}') or '{}'),
                }
            return None
        except Exception as e:
            print(f"[Logging] Error getting settings: {e}")
            return None

    def get_log_channel(self, settings: dict, category: str, log_type: str) -> str | None:
        """Get the channel ID for a specific log type"""
        # First check type-specific override
        if log_type in settings.get('type_channels', {}):
            return settings['type_channels'][log_type]
        # Then check category channel
        if category in settings.get('category_channels', {}):
            return settings['category_channels'][category]
        return None

    def should_ignore(self, settings: dict, user: discord.Member = None, channel: discord.TextChannel = None) -> bool:
        """Check if this action should be ignored"""
        if user:
            # Check ignored users
            if str(user.id) in settings.get('ignored_users', []):
                return True
            # Check ignored roles
            for role in user.roles:
                if str(role.id) in settings.get('ignored_roles', []):
                    return True
        
        if channel and str(channel.id) in settings.get('ignored_channels', []):
            return True
        
        return False

    async def send_log(self, guild: discord.Guild, category: str, log_type: str, embed: discord.Embed, 
                       user: discord.Member = None, channel: discord.TextChannel = None):
        """Send a log message to the appropriate channel"""
        settings = self.get_settings(guild.id)
        if not settings:
            return
        
        # Check if should ignore
        if self.should_ignore(settings, user, channel):
            return
        
        # Get log channel
        channel_id = self.get_log_channel(settings, category, log_type)
        if not channel_id:
            return
        
        log_channel = guild.get_channel(int(channel_id))
        if not log_channel:
            return
        
        try:
            # Add timestamp footer
            embed.timestamp = datetime.utcnow()
            
            if settings.get('use_webhooks'):
                # Try to use webhook
                webhook = await self._get_or_create_webhook(log_channel)
                if webhook:
                    await webhook.send(embed=embed, username="Don Pollo Logs", avatar_url=self.bot.user.display_avatar.url)
                    return
            
            # Fallback to regular message
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"[Logging] Error sending log: {e}")

    async def _get_or_create_webhook(self, channel: discord.TextChannel) -> discord.Webhook | None:
        """Get or create a webhook for logging"""
        try:
            if channel.id in self.webhook_cache:
                return self.webhook_cache[channel.id]
            
            webhooks = await channel.webhooks()
            for wh in webhooks:
                if wh.name == "Don Pollo Logs":
                    self.webhook_cache[channel.id] = wh
                    return wh
            
            # Create new webhook
            webhook = await channel.create_webhook(name="Don Pollo Logs")
            self.webhook_cache[channel.id] = webhook
            return webhook
        except:
            return None

    # ==================== MESSAGE EVENTS ====================
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=0xFF6B6B,
            description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}"
        )
        if message.content:
            content = message.content[:1000] + "..." if len(message.content) > 1000 else message.content
            embed.add_field(name="Content", value=content, inline=False)
        
        # Show attachment details
        if message.attachments:
            attachment_info = []
            first_image = None
            for att in message.attachments:
                size_kb = att.size / 1024
                size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"
                attachment_info.append(f"📎 **{att.filename}** ({size_str})")
                # Check if it's an image to show preview
                if first_image is None and att.content_type and att.content_type.startswith('image/'):
                    first_image = att.proxy_url or att.url
            
            embed.add_field(name=f"Attachments ({len(message.attachments)})", value="\n".join(attachment_info[:5]), inline=False)
            
            # Set image preview if available (using proxy_url which may still be cached)
            if first_image:
                embed.set_image(url=first_image)
        
        embed.set_footer(text=f"User ID: {message.author.id}")
        
        await self.send_log(message.guild, "messages", "message_delete", embed, message.author, message.channel)

    @commands.Cog.listener()  
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=0xFFD700,
            description=f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n[Jump to message]({after.jump_url})"
        )
        if before.content:
            old = before.content[:500] + "..." if len(before.content) > 500 else before.content
            embed.add_field(name="Before", value=old, inline=False)
        if after.content:
            new = after.content[:500] + "..." if len(after.content) > 500 else after.content
            embed.add_field(name="After", value=new, inline=False)
        embed.set_footer(text=f"User ID: {before.author.id}")
        
        await self.send_log(before.guild, "messages", "message_edit", embed, before.author, before.channel)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        if not messages or not messages[0].guild:
            return
        
        embed = discord.Embed(
            title="🗑️ Bulk Message Delete",
            color=0xFF6B6B,
            description=f"**{len(messages)}** messages deleted in {messages[0].channel.mention}"
        )
        embed.set_footer(text=f"Channel ID: {messages[0].channel.id}")
        
        await self.send_log(messages[0].guild, "messages", "message_bulk_delete", embed)

    # ==================== MEMBER EVENTS ====================
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            title="📥 Member Joined",
            color=0x57F287,
            description=f"{member.mention} joined the server"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Member Count", value=str(member.guild.member_count), inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.send_log(member.guild, "users", "member_join", embed, member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = discord.Embed(
            title="📤 Member Left",
            color=0xED4245,
            description=f"**{member.display_name}** ({member.name}) left the server"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        roles = [r.mention for r in member.roles if r.name != "@everyone"][:10]
        if roles:
            embed.add_field(name="Roles", value=", ".join(roles), inline=False)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.send_log(member.guild, "users", "member_leave", embed, member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Nickname change
        if before.nick != after.nick:
            embed = discord.Embed(
                title="📝 Nickname Changed",
                color=0xFFD700,
                description=f"{after.mention}"
            )
            embed.add_field(name="Before", value=before.nick or "None", inline=True)
            embed.add_field(name="After", value=after.nick or "None", inline=True)
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"User ID: {after.id}")
            await self.send_log(after.guild, "users", "member_nickname_update", embed, after)
        
        # Role changes
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        
        added = after_roles - before_roles
        removed = before_roles - after_roles
        
        if added or removed:
            embed = discord.Embed(
                title="🎭 Roles Updated",
                color=0x5865F2,
                description=f"{after.mention}"
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            if added:
                embed.add_field(name="Added", value=", ".join([r.mention for r in added]), inline=True)
            if removed:
                embed.add_field(name="Removed", value=", ".join([r.mention for r in removed]), inline=True)
            embed.set_footer(text=f"User ID: {after.id}")
            await self.send_log(after.guild, "users", "member_roles_update", embed, after)

    # ==================== CHANNEL EVENTS ====================
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        embed = discord.Embed(
            title="📁 Channel Created",
            color=0x57F287,
            description=f"**{channel.name}**"
        )
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title(), inline=True)
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await self.send_log(channel.guild, "channels", "channel_create", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        embed = discord.Embed(
            title="🗑️ Channel Deleted",
            color=0xED4245,
            description=f"**{channel.name}**"
        )
        embed.add_field(name="Type", value=str(channel.type).replace("_", " ").title(), inline=True)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await self.send_log(channel.guild, "channels", "channel_delete", embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if hasattr(before, 'topic') and before.topic != after.topic:
            changes.append(f"**Topic:** Changed")
        if hasattr(before, 'nsfw') and before.nsfw != after.nsfw:
            changes.append(f"**NSFW:** {before.nsfw} → {after.nsfw}")
        if hasattr(before, 'slowmode_delay') and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"**Slowmode:** {before.slowmode_delay}s → {after.slowmode_delay}s")
        
        if not changes:
            return
        
        embed = discord.Embed(
            title="✏️ Channel Updated",
            color=0xFFD700,
            description=f"{after.mention}\n\n" + "\n".join(changes)
        )
        embed.set_footer(text=f"Channel ID: {after.id}")
        
        await self.send_log(after.guild, "channels", "channel_name_update", embed)

    # ==================== ROLE EVENTS ====================
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = discord.Embed(
            title="🎭 Role Created",
            color=role.color if role.color.value else 0x57F287,
            description=f"**{role.name}**"
        )
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await self.send_log(role.guild, "roles", "role_create", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = discord.Embed(
            title="🗑️ Role Deleted",
            color=0xED4245,
            description=f"**{role.name}**"
        )
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await self.send_log(role.guild, "roles", "role_delete", embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if before.color != after.color:
            changes.append(f"**Color:** {before.color} → {after.color}")
        if before.hoist != after.hoist:
            changes.append(f"**Hoisted:** {before.hoist} → {after.hoist}")
        if before.mentionable != after.mentionable:
            changes.append(f"**Mentionable:** {before.mentionable} → {after.mentionable}")
        
        if not changes:
            return
        
        embed = discord.Embed(
            title="✏️ Role Updated",
            color=after.color if after.color.value else 0xFFD700,
            description=f"**{after.name}**\n\n" + "\n".join(changes)
        )
        embed.set_footer(text=f"Role ID: {after.id}")
        
        await self.send_log(after.guild, "roles", "role_name_update", embed)

    # ==================== VOICE EVENTS ====================
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        settings = self.get_settings(member.guild.id)
        if settings and settings.get('ignore_voice_users') and self.should_ignore(settings, member):
            return
        
        if before.channel is None and after.channel is not None:
            # Joined voice
            embed = discord.Embed(
                title="🎙️ Joined Voice",
                color=0x57F287,
                description=f"{member.mention} joined **{after.channel.name}**"
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            await self.send_log(member.guild, "voice", "voice_channel_join", embed, member)
        
        elif before.channel is not None and after.channel is None:
            # Left voice
            embed = discord.Embed(
                title="🎙️ Left Voice",
                color=0xED4245,
                description=f"{member.mention} left **{before.channel.name}**"
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            await self.send_log(member.guild, "voice", "voice_channel_leave", embed, member)
        
        elif before.channel != after.channel:
            # Moved channels
            embed = discord.Embed(
                title="🎙️ Moved Voice Channel",
                color=0xFFD700,
                description=f"{member.mention}"
            )
            embed.add_field(name="From", value=before.channel.name, inline=True)
            embed.add_field(name="To", value=after.channel.name, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            await self.send_log(member.guild, "voice", "voice_channel_move", embed, member)

    # ==================== INVITE EVENTS ====================
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        embed = discord.Embed(
            title="🔗 Invite Created",
            color=0x57F287,
            description=f"**Code:** `{invite.code}`"
        )
        embed.add_field(name="Channel", value=invite.channel.mention, inline=True)
        if invite.inviter:
            embed.add_field(name="Created by", value=invite.inviter.mention, inline=True)
        if invite.max_uses:
            embed.add_field(name="Max Uses", value=str(invite.max_uses), inline=True)
        embed.set_footer(text=f"Invite Code: {invite.code}")
        
        await self.send_log(invite.guild, "invites", "invite_create", embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        embed = discord.Embed(
            title="🔗 Invite Deleted",
            color=0xED4245,
            description=f"**Code:** `{invite.code}`"
        )
        embed.add_field(name="Channel", value=invite.channel.mention, inline=True)
        embed.set_footer(text=f"Invite Code: {invite.code}")
        
        await self.send_log(invite.guild, "invites", "invite_delete", embed)

    # ==================== MODERATION EVENTS ====================
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        embed = discord.Embed(
            title="🔨 Member Banned",
            color=0xED4245,
            description=f"**{user.name}** was banned from the server"
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        await self.send_log(guild, "moderation", "mod_ban", embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        embed = discord.Embed(
            title="✅ Member Unbanned",
            color=0x57F287,
            description=f"**{user.name}** was unbanned from the server"
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        await self.send_log(guild, "moderation", "mod_unban", embed)


async def setup(bot):
    await bot.add_cog(Logging(bot))
