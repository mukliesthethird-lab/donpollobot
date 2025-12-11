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
        if log_type in settings.get('types', {}): # Fallback or deprecated structure
             pass 

        # First check type-specific override
        if log_type in settings.get('type_channels', {}):
            return settings['type_channels'][log_type]
        # Then check category channel
        if category in settings.get('category_channels', {}):
             return settings['category_channels'][category]
        return None
        
    async def get_audit_log_entry(self, guild: discord.Guild, action, target_id: int = None):
        """Helper to get the most recent audit log entry for an action"""
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if target_id and entry.target.id == target_id:
                     return entry
            return None
        except:
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
            color=0xFF4500, # Red-Orange
            description=f"**User:** {message.author.mention} (`{message.author.id}`)\n**Channel:** {message.channel.mention}"
        )
        embed.set_author(name=f"{message.author.display_name}", icon_url=message.author.display_avatar.url)
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
        if not before.guild or before.author.bot:
            return

        # Check for Pin/Unpin
        if before.pinned != after.pinned:
            # We don't easily know WHO pinned it without audit logs, but the event gives us the message state.
            # Usually audit log is needed for "Pinned by", but standard event just shows message change.
            # We will use formatting to match the "Message pinned" style.
            
            content = after.content[:100] + "..." if len(after.content) > 100 else after.content
            if not content and after.attachments: content = "[Attachment]"
            
            description = (
                f"**Channel:** {after.channel.name} ({after.channel.mention})\n"
                f"**Message:** {content}\n"
                f"**Message ID:** `{after.id}`\n"
                f"**Message author:** {after.author.mention} (`{after.author.id}`)\n"
                f"[Jump to message]({after.jump_url})"
            )

            if after.pinned:
                embed = discord.Embed(
                    title="Message pinned",
                    color=0x3498DB, # Blue
                    description=description
                )
                embed.set_author(name=after.author.name, icon_url=after.author.display_avatar.url)
                embed.set_footer(text=f"ID: {after.author.id}") # Author ID in footer per image? Or Message ID? Image shows User ID.
                await self.send_log(after.guild, "messages", "message_pin", embed, after.author, after.channel)
            else:
                embed = discord.Embed(
                    title="Message unpinned",
                    color=0x3498DB, # Blue
                    description=description
                )
                embed.set_author(name=after.author.name, icon_url=after.author.display_avatar.url)
                embed.set_footer(text=f"ID: {after.author.id}")
                await self.send_log(after.guild, "messages", "message_unpin", embed, after.author, after.channel)
            return

        if before.content == after.content:
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=0xFFA500, # Orange
            description=f"**User:** {before.author.mention}\n**Channel:** {before.channel.mention}\n[👉 Jump to message]({after.jump_url})"
        )
        embed.set_author(name=f"{before.author.display_name}", icon_url=before.author.display_avatar.url)
        if before.content:
            old = before.content[:1000] + "..." if len(before.content) > 1000 else before.content
            embed.add_field(name="📄 Before", value=old, inline=False)
        if after.content:
            new = after.content[:1000] + "..." if len(after.content) > 1000 else after.content
            embed.add_field(name="📝 After", value=new, inline=False)
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

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member | discord.User):
        if user.bot:
            return
        
        message = reaction.message
        if not message.guild:
            return

        embed = discord.Embed(
            title="😀 Reaction Added",
            color=0xFEE75C,
            description=f"**User:** {user.mention}\n**Channel:** {message.channel.mention}\n**Emoji:** {reaction.emoji}\n[Jump to message]({message.jump_url})"
        )
        embed.set_footer(text=f"User ID: {user.id}")
        
        await self.send_log(message.guild, "messages", "reaction_add", embed, user, message.channel)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member | discord.User):
        if user.bot:
            return
            
        message = reaction.message
        if not message.guild:
            return

        embed = discord.Embed(
            title="😕 Reaction Removed",
            color=0xFEE75C,
            description=f"**User:** {user.mention}\n**Channel:** {message.channel.mention}\n**Emoji:** {reaction.emoji}\n[Jump to message]({message.jump_url})"
        )
        embed.set_footer(text=f"User ID: {user.id}")
        
        await self.send_log(message.guild, "messages", "reaction_remove", embed, user, message.channel)

    @commands.Cog.listener()
    async def on_reaction_clear(self, message: discord.Message, reactions: list[discord.Reaction]):
        if not message.guild:
            return

        embed = discord.Embed(
            title="🧹 Reactions Cleared",
            color=0xED4245,
            description=f"All reactions cleared from message in {message.channel.mention}\n[Jump to message]({message.jump_url})"
        )
        embed.set_footer(text=f"Message ID: {message.id}")
        
        await self.send_log(message.guild, "messages", "reaction_clear", embed, None, message.channel)

    # ==================== MEMBER EVENTS ====================
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            title="� Member Joined",
            color=0x00FF7F, # SpringGreen
            description=f"{member.mention} **{member.display_name}**"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🗓️ Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="📊 Member Count", value=f"#{member.guild.member_count}", inline=True)
        if member.bot:
             embed.add_field(name="🤖 Bot", value="Yes", inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.send_log(member.guild, "users", "member_join", embed, member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = discord.Embed(
            title="� Member Left",
            color=0xDC143C, # Crimson
            description=f"{member.mention} **{member.display_name}**"
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
                title="Nickname update",
                color=0xFFD700,
                description=f"**User:** {after.name} ({after.mention})\n**Before:** {before.nick or 'None'}\n**After:** {after.nick or 'None'}"
            )
            embed.set_author(name=after.name, icon_url=after.display_avatar.url)
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"ID: {after.id}")
            await self.send_log(after.guild, "users", "member_nickname_update", embed, after)
        
        # Role changes
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        
        added = after_roles - before_roles
        removed = before_roles - after_roles
        
        if added or removed:
            description = f"**User:** {after.name} ({after.mention})\n"
            if added:
                description += f"**Added:** {', '.join([r.mention for r in added])}\n"
            if removed:
                description += f"**Removed:** {', '.join([r.mention for r in removed])}"

            embed = discord.Embed(
                title="User roles update",
                color=0xFFA500, # Orange
                description=description
            )
            embed.set_author(name=after.name, icon_url=after.display_avatar.url)
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"ID: {after.id}")
            await self.send_log(after.guild, "users", "member_roles_update", embed, after)

        # Pending (Verification) Update
        if before.pending != after.pending:
            status = "Verified" if not after.pending else "Pending"
            embed = discord.Embed(
                title="Member verified",
                color=0x57F287 if not after.pending else 0xFFA500,
                description=f"**User:** {after.name} ({after.mention})\n**Status:** {status}"
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"ID: {after.id}")
            await self.send_log(after.guild, "users", "member_update", embed, after)

        # Avatar change
        if before.display_avatar.url != after.display_avatar.url:
             embed = discord.Embed(
                title="Avatar update",
                color=0x3498DB, # Blueish
                description=f"{after.mention}"
            )
             embed.set_author(name=after.name, icon_url=after.display_avatar.url)
             embed.set_thumbnail(url=after.display_avatar.url)
             embed.set_footer(text=f"ID: {after.id}")
             await self.send_log(after.guild, "users", "member_avatar_update", embed, after)

        # Timeout (Communication Disabled)
        if not before.timed_out_until and after.timed_out_until:
            embed = discord.Embed(
                title="Member timed out",
                color=0x000000, 
                description=f"**User:** {after.name} ({after.mention})\n**Ends:** <t:{int(after.timed_out_until.timestamp())}:R>"
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            
            # Try to fetch audit log for reason/moderator
            entry = await self.get_audit_log_entry(after.guild, discord.AuditLogAction.member_update, after.id)
            if entry and entry.user:
                 embed.description += f"\n**Moderator:** {entry.user.mention}"
            if entry and entry.reason:
                 embed.description += f"\n**Reason:** {entry.reason}"
                 
            embed.set_footer(text=f"ID: {after.id}")
            await self.send_log(after.guild, "moderation", "mod_timeout", embed, after)

        # Timeout Removed
        elif before.timed_out_until and not after.timed_out_until:
             embed = discord.Embed(
                title="Timeout removed",
                color=0x00FF7F, 
                description=f"**User:** {after.name} ({after.mention})"
            )
             embed.set_thumbnail(url=after.display_avatar.url)
             # Try to fetch audit log
             entry = await self.get_audit_log_entry(after.guild, discord.AuditLogAction.member_update, after.id)
             if entry and entry.user:
                 embed.description += f"\n**Moderator:** {entry.user.mention}"
             
             embed.set_footer(text=f"ID: {after.id}")
             await self.send_log(after.guild, "moderation", "mod_timeout_remove", embed, after)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        # Username/Global name update
        if before.name != after.name or before.global_name != after.global_name:
             # We need to find mutual guilds to log this
             for guild in self.bot.guilds:
                 if guild.get_member(after.id):
                     embed = discord.Embed(
                        title="👤 Username Updated",
                        color=0xFFA500,
                        description=f"{after.mention} changed their username"
                    )
                     embed.add_field(name="Before", value=f"{before.name} ({before.global_name or 'None'})", inline=False)
                     embed.add_field(name="After", value=f"{after.name} ({after.global_name or 'None'})", inline=False)
                     embed.set_thumbnail(url=after.display_avatar.url)
                     embed.set_footer(text=f"User ID: {after.id}")
                     await self.send_log(guild, "users", "user_update", embed, guild.get_member(after.id))

        # Avatar update (Global)
        if before.display_avatar.url != after.display_avatar.url:
             for guild in self.bot.guilds:
                 member = guild.get_member(after.id)
                 if member:
                     # Check if member uses a guild specific avatar (if so, we ignore global update here to avoid duplicate or handled by member_update?)
                     # Actually, if they have guild avatar, display_avatar is guild avatar.
                     # If they change global avatar, and have no guild avatar, their display_avatar changes.
                     # on_member_update might handle it if cache updates.
                     # But purely for "Member Avatar Update" logging:
                     if member.guild_avatar is None: # Only log if they use global avatar
                         embed = discord.Embed(
                            title="🖼️ Avatar Updated (Global)",
                            color=0xFFA500,
                            description=f"{member.mention} **{member.display_name}**"
                        )
                         embed.set_thumbnail(url=after.display_avatar.url)
                         embed.set_footer(text=f"User ID: {after.id}")
                         await self.send_log(guild, "users", "member_avatar_update", embed, member)

    # ==================== EMOJI EVENTS ====================

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: list[discord.Emoji], after: list[discord.Emoji]):
        # Removed
        for emoji in before:
            if emoji not in after:
                embed = discord.Embed(title="🗑️ Emoji Deleted", color=0xED4245, description=f"**{emoji.name}**")
                embed.set_thumbnail(url=emoji.url)
                embed.set_footer(text=f"Emoji ID: {emoji.id}")
                await self.send_log(guild, "emojis", "emoji_delete", embed)
        
        # Added
        for emoji in after:
            if emoji not in before:
                embed = discord.Embed(title="😀 Emoji Created", color=0x57F287, description=f"{emoji} **{emoji.name}**")
                embed.set_thumbnail(url=emoji.url)
                if emoji.user:
                     embed.add_field(name="Created by", value=emoji.user.mention, inline=True)
                embed.set_footer(text=f"Emoji ID: {emoji.id}")
                await self.send_log(guild, "emojis", "emoji_create", embed)

        # Updated name
        # Mapping IDs to objects for easy cleanup
        before_map = {e.id: e for e in before}
        for emoji in after:
             if emoji.id in before_map:
                 old = before_map[emoji.id]
                 if old.name != emoji.name:
                      embed = discord.Embed(title="✏️ Emoji Updated", color=0xFFA500, description=f"{emoji} **{emoji.name}**")
                      embed.add_field(name="Before", value=old.name, inline=True)
                      embed.add_field(name="After", value=emoji.name, inline=True)
                      embed.set_thumbnail(url=emoji.url)
                      embed.set_footer(text=f"Emoji ID: {emoji.id}")
                      await self.send_log(guild, "emojis", "emoji_update", embed)


    # ==================== STICKER EVENTS ====================

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before: list[discord.GuildSticker], after: list[discord.GuildSticker]):
        # Removed
        for sticker in before:
            if sticker not in after:
                embed = discord.Embed(title="🗑️ Sticker Deleted", color=0xED4245, description=f"**{sticker.name}**")
                embed.set_thumbnail(url=sticker.url)
                embed.set_footer(text=f"Sticker ID: {sticker.id}")
                await self.send_log(guild, "stickers", "sticker_delete", embed)
        
        # Added
        for sticker in after:
            if sticker not in before:
                embed = discord.Embed(title="🏷️ Sticker Created", color=0x57F287, description=f"**{sticker.name}**")
                embed.set_thumbnail(url=sticker.url)
                embed.set_footer(text=f"Sticker ID: {sticker.id}")
                await self.send_log(guild, "stickers", "sticker_create", embed)
        
        # Updated
        before_map = {s.id: s for s in before}
        for sticker in after:
             if sticker.id in before_map:
                 old = before_map[sticker.id]
                 if old.name != sticker.name:
                      embed = discord.Embed(title="✏️ Sticker Updated", color=0xFFA500, description=f"**{sticker.name}**")
                      embed.add_field(name="Before", value=old.name, inline=True)
                      embed.add_field(name="After", value=sticker.name, inline=True)
                      embed.set_thumbnail(url=sticker.url)
                      embed.set_footer(text=f"Sticker ID: {sticker.id}")
                      await self.send_log(guild, "stickers", "sticker_update", embed) 

    # ==================== THREAD EVENTS ====================
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
         embed = discord.Embed(title="🧵 Thread Created", color=0x57F287, description=f"{thread.mention} (`{thread.name}`)")
         embed.add_field(name="Parent Channel", value=thread.parent.mention if thread.parent else "Unknown", inline=True)
         embed.set_footer(text=f"Thread ID: {thread.id}")
         await self.send_log(thread.guild, "threads", "thread_create", embed)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
         embed = discord.Embed(title="🗑️ Thread Deleted", color=0xED4245, description=f"**{thread.name}**")
         if thread.parent:
             embed.add_field(name="Parent Channel", value=thread.parent.mention, inline=True)
         embed.set_footer(text=f"Thread ID: {thread.id}")
         await self.send_log(thread.guild, "threads", "thread_delete", embed)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
         if before.name != after.name:
             embed = discord.Embed(title="✏️ Thread Updated", color=0xFFA500, description=f"{after.mention} (`{after.name}`)")
             embed.add_field(name="Before", value=before.name, inline=True)
             embed.add_field(name="After", value=after.name, inline=True)
             embed.set_footer(text=f"Thread ID: {after.id}")
             await self.send_log(after.guild, "threads", "thread_update", embed)
         
         if before.archived != after.archived:
             status = "Archived" if after.archived else "Unarchived"
             color = 0xFFA500 if after.archived else 0x57F287
             embed = discord.Embed(title=f"📦 Thread {status}", color=color, description=f"{after.mention}")
             embed.set_footer(text=f"Thread ID: {after.id}")
             await self.send_log(after.guild, "threads", "thread_update", embed)
             
    # ==================== WEBHOOK EVENTS ====================

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.TextChannel):
         # This event is generic, we have to fetch webhooks to know what happened
         # For simplicity, we might just log "Webhooks Updated in Channel"
         # Or we could try to diff if we cached them, but that's expensive.
         # A simple log is better than none.
         embed = discord.Embed(title="🔌 Webhooks Updated", color=0xFFA500, description=f"Webhooks changed in {channel.mention}")
         embed.set_footer(text=f"Channel ID: {channel.id}")
         await self.send_log(channel.guild, "webhooks", "webhook_update", embed)

    # ==================== CHANNEL EVENTS ====================
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        embed = discord.Embed(
            title="Text channel created",
            color=0x57F287, # Green
            description=f"**Name:** {channel.name} ({channel.mention})\n**ID:** `{channel.id}`\n**Category:** {channel.category.name if channel.category else 'None'} `{channel.category.id if channel.category else 'None'}`\n**Position:** {channel.position}"
        )
        embed.set_footer(text=f"ID: {channel.id}")
        
        await self.send_log(channel.guild, "channels", "channel_create", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        embed = discord.Embed(
            title="Text channel deleted",
            color=0xED4245, # Red
            description=f"**Name:** {channel.name}\n**ID:** `{channel.id}`\n**Category:** {channel.category.name if channel.category else 'None'} `{channel.category.id if channel.category else 'None'}`"
        )
        embed.set_footer(text=f"ID: {channel.id}")
        
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
        if before.bitrate != after.bitrate:
             changes.append(f"**Bitrate:** {before.bitrate//1000}kbps → {after.bitrate//1000}kbps")
        if before.user_limit != after.user_limit:
             limit_b = before.user_limit or "∞"
             limit_a = after.user_limit or "∞"
             changes.append(f"**User Limit:** {limit_b} → {limit_a}")
        if hasattr(before, 'rtc_region') and before.rtc_region != after.rtc_region:
             changes.append(f"**Region:** {before.rtc_region or 'Auto'} → {after.rtc_region or 'Auto'}")
        if hasattr(before, 'video_quality_mode') and before.video_quality_mode != after.video_quality_mode:
             changes.append(f"**Video Quality:** {before.video_quality_mode} → {after.video_quality_mode}")
        if hasattr(before, 'category') and before.category != after.category:
             cat_b = before.category.name if before.category else "None"
             cat_a = after.category.name if after.category else "None"
             changes.append(f"**Category:** {cat_b} → {cat_a}")
        
        # Permissions Overwrites (Simplified check)
        if before.overwrites != after.overwrites:
             changes.append("**Permissions:** Overrides updated")

        if not changes:
            return
        
        embed = discord.Embed(
            title="✏️ Channel Updated",
            color=0xFFA500,
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
        if before.icon != after.icon:
            changes.append("**Icon:** Updated")
        
        if before.permissions != after.permissions:
             diff = []
             for perm, value in after.permissions:
                 if value != getattr(before.permissions, perm):
                     op = "+" if value else "-"
                     diff.append(f"{op}{perm.replace('_', ' ').title()}")
             if diff:
                 changes.append(f"**Permissions:** {', '.join(diff)}") # Truncate if too long?

        if before.position != after.position:
             embed = discord.Embed(title="↕️ Role Position Updated", color=0xFFA500, description=f"**{after.name}**\n**Position:** {before.position} → {after.position}")
             embed.set_footer(text=f"Role ID: {after.id}")
             await self.send_log(after.guild, "roles", "role_position_update", embed)
        
        if not changes:
            return
        
        embed = discord.Embed(
            title="✏️ Role Updated",
            color=after.color if after.color.value else 0xFFA500,
            description=f"{after.mention} **{after.name}**\n\n" + "\n".join(changes[:10]) + ("\n..." if len(changes) > 10 else "")
        )
        embed.set_footer(text=f"Role ID: {after.id}")
        
        await self.send_log(after.guild, "roles", "role_name_update", embed)

    # ==================== APPLICATION (INTEGRATION) EVENTS ====================
    
    @commands.Cog.listener()
    async def on_integration_create(self, integration):
        embed = discord.Embed(title="🤖 App/Integration Added", color=0x57F287, description=f"**{integration.name}**")
        if integration.user:
             embed.add_field(name="Bot User", value=integration.user.mention, inline=True)
        embed.set_footer(text=f"ID: {integration.id}")
        await self.send_log(integration.guild, "applications", "app_add", embed)

    @commands.Cog.listener()
    async def on_integration_delete(self, integration):
         embed = discord.Embed(title="🗑️ App/Integration Removed", color=0xED4245, description=f"**{integration.name}**")
         embed.set_footer(text=f"ID: {integration.id}")
         await self.send_log(integration.guild, "applications", "app_remove", embed)

    # ==================== SOUNDBOARD EVENTS ====================

    @commands.Cog.listener()
    async def on_soundboard_sound_create(self, sound):
         embed = discord.Embed(title="🔊 Soundboard Sound Created", color=0x57F287, description=f"**{sound.name}**")
         embed.add_field(name="Emoji", value=str(sound.emoji) if sound.emoji else "None", inline=True)
         if sound.user:
             embed.add_field(name="Created by", value=sound.user.mention, inline=True)
         embed.set_footer(text=f"Sound ID: {sound.id}")
         await self.send_log(sound.guild, "soundboard", "soundboard_sound_create", embed)

    @commands.Cog.listener()
    async def on_soundboard_sound_delete(self, sound):
         embed = discord.Embed(title="🗑️ Soundboard Sound Deleted", color=0xED4245, description=f"**{sound.name}**")
         embed.set_footer(text=f"Sound ID: {sound.id}")
         await self.send_log(sound.guild, "soundboard", "soundboard_sound_delete", embed)

    @commands.Cog.listener()
    async def on_soundboard_sound_update(self, before, after):
         if before.name != after.name or before.emoji != after.emoji or before.volume != after.volume:
             embed = discord.Embed(title="✏️ Soundboard Sound Updated", color=0xFFA500, description=f"**{after.name}**")
             if before.name != after.name:
                 embed.add_field(name="Name", value=f"{before.name} → {after.name}", inline=True)
             if before.volume != after.volume:
                 embed.add_field(name="Volume", value=f"{before.volume} → {after.volume}", inline=True)
             embed.set_footer(text=f"Sound ID: {after.id}")
             await self.send_log(after.guild, "soundboard", "soundboard_sound_update", embed)

    # ==================== SCHEDULED EVENT EVENTS ====================

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event):
         embed = discord.Embed(title="📅 Event Created", color=0x57F287, description=f"**{event.name}**")
         embed.add_field(name="Start Time", value=f"<t:{int(event.start_time.timestamp())}:F>", inline=True)
         if event.location:
             embed.add_field(name="Location", value=event.location, inline=True)
         embed.set_footer(text=f"Event ID: {event.id}")
         await self.send_log(event.guild, "events", "event_create", embed)

    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event):
         embed = discord.Embed(title="🗑️ Event Deleted", color=0xED4245, description=f"**{event.name}**")
         embed.set_footer(text=f"Event ID: {event.id}")
         await self.send_log(event.guild, "events", "event_delete", embed)

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before, after):
         changes = []
         if before.name != after.name: changes.append(f"**Name:** {before.name} → {after.name}")
         if before.status != after.status: changes.append(f"**Status:** {before.status} → {after.status}")
         if before.location != after.location: changes.append("**Location:** Updated")
         
         if changes:
             embed = discord.Embed(title="✏️ Event Updated", color=0xFFA500, description=f"**{after.name}**\n" + "\n".join(changes))
             embed.set_footer(text=f"Event ID: {after.id}")
             await self.send_log(after.guild, "events", "event_update", embed)

    @commands.Cog.listener()
    async def on_scheduled_event_user_add(self, event, user):
         embed = discord.Embed(title="✅ User Interest Added", color=0x57F287, description=f"{user.mention} is interested in **{event.name}**")
         embed.set_footer(text=f"Event ID: {event.id}")
         await self.send_log(event.guild, "events", "event_user_add", embed)

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, event, user):
         embed = discord.Embed(title="❌ User Interest Removed", color=0xED4245, description=f"{user.mention} is no longer interested in **{event.name}**")
         embed.set_footer(text=f"Event ID: {event.id}")
         await self.send_log(event.guild, "events", "event_user_remove", embed)

    # ==================== AUTOMOD EVENTS ====================

    @commands.Cog.listener()
    async def on_automod_rule_create(self, rule):
        embed = discord.Embed(title="🤖 AutoMod Rule Created", color=0x57F287, description=f"**{rule.name}**")
        embed.add_field(name="Creator", value=f"<@{rule.creator_id}>", inline=True)
        embed.add_field(name="Trigger", value=str(rule.trigger_type).split('.')[-1], inline=True)
        embed.set_footer(text=f"Rule ID: {rule.id}")
        await self.send_log(rule.guild, "automod", "automod_rule_create", embed)

    @commands.Cog.listener()
    async def on_automod_rule_delete(self, rule):
        embed = discord.Embed(title="🤖 AutoMod Rule Deleted", color=0xED4245, description=f"**{rule.name}**")
        embed.set_footer(text=f"Rule ID: {rule.id}")
        await self.send_log(rule.guild, "automod", "automod_rule_delete", embed)

    @commands.Cog.listener()
    async def on_automod_rule_update(self, before, after):
        embed = discord.Embed(title="🤖 AutoMod Rule Updated", color=0xFFA500, description=f"**{after.name}**")
        embed.set_footer(text=f"Rule ID: {after.id}")
        await self.send_log(after.guild, "automod", "automod_rule_update", embed)

    @commands.Cog.listener()
    async def on_automod_action(self, execution):
        embed = discord.Embed(title="🛡️ AutoMod Action Executed", color=0xED4245, description=f"**Rule:** {execution.rule_trigger_type}")
        if execution.member:
             embed.add_field(name="User", value=execution.member.mention, inline=True)
        if execution.channel:
             embed.add_field(name="Channel", value=execution.channel.mention, inline=True)
        if execution.content:
             embed.add_field(name="Content", value=execution.content[:500], inline=False)
        embed.set_footer(text=f"Rule ID: {execution.rule_id}")
        await self.send_log(execution.guild, "automod", "automod_action_execute", embed)

    # ==================== POLL EVENTS ====================
    # Polls are tricky as there are no direct events for creation/end in discord.py usually
    # But voting is on_raw_poll_vote_add? No, standard is raw_reaction_add for older polls?
    # New polls are message components.
    # We will try on_poll_vote_add if available (Discord.py 2.4+)
    
    @commands.Cog.listener()
    async def on_poll_vote_add(self, user, answer):
         if user.bot: return
         embed = discord.Embed(title="📊 Poll Vote Added", color=0x57F287, description=f"{user.mention} voted on poll")
         embed.add_field(name="Answer", value=str(answer), inline=True)
         embed.set_footer(text=f"Poll ID: {answer.poll.message.id}")
         await self.send_log(user.guild, "polls", "poll_vote_add", embed)

    @commands.Cog.listener()
    async def on_poll_vote_remove(self, user, answer):
         if user.bot: return
         embed = discord.Embed(title="📊 Poll Vote Removed", color=0xED4245, description=f"{user.mention} removed vote")
         embed.add_field(name="Answer", value=str(answer), inline=True)
         embed.set_footer(text=f"Poll ID: {answer.poll.message.id}")
         await self.send_log(user.guild, "polls", "poll_vote_remove", embed)

    # ==================== VOICE EVENTS ====================
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        settings = self.get_settings(member.guild.id)
        if settings and settings.get('ignore_voice_users') and self.should_ignore(settings, member):
            return
        
        if before.channel is None and after.channel is not None:
            # Joined voice
            limit = str(after.channel.user_limit) if after.channel.user_limit else "∞"
            embed = discord.Embed(
                title="User joined channel",
                color=0x57F287,
                description=f"**User:** {member.name} ({member.mention})\n**Channel:** 🔊 {after.channel.mention}\n**Users:** {len(after.channel.members)}/{limit}"
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"ID: {member.id}")
            await self.send_log(member.guild, "voice", "voice_channel_join", embed, member)
        
        elif before.channel is not None and after.channel is None:
            # Left voice
            limit = str(before.channel.user_limit) if before.channel.user_limit else "∞"
            embed = discord.Embed(
                title="User left channel",
                color=0xED4245,
                description=f"**User:** {member.name} ({member.mention})\n**Channel:** 🔊 {before.channel.mention}\n**Users:** {len(before.channel.members)}/{limit}"
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"ID: {member.id}")
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
            
        # Mute/Deafen status
        if before.self_mute != after.self_mute:
            action = "Muted" if after.self_mute else "Unmuted"
            icon = "🔇" if after.self_mute else "🔊"
            embed = discord.Embed(title=f"{icon} Voice {action} (Self)", color=0xFFA500, description=f"{member.mention}")
            await self.send_log(member.guild, "voice", "voice_mute", embed, member)
            
        if before.self_deaf != after.self_deaf:
            action = "Deafened" if after.self_deaf else "Undeafened"
            icon = "🙉" if after.self_deaf else "👂"
            embed = discord.Embed(title=f"{icon} Voice {action} (Self)", color=0xFFA500, description=f"{member.mention}")
            await self.send_log(member.guild, "voice", "voice_deafen", embed, member)

        if before.mute != after.mute:
            action = "Server Muted" if after.mute else "Server Unmuted"
            icon = "🔇" if after.mute else "🔊"
            embed = discord.Embed(title=f"{icon} Voice {action}", color=0xED4245 if after.mute else 0x57F287, description=f"{member.mention}")
            # Try audit log for moderator
            entry = await self.get_audit_log_entry(member.guild, discord.AuditLogAction.member_update, member.id)
            if entry and entry.user:
                 embed.add_field(name="Moderator", value=entry.user.mention, inline=True)
            await self.send_log(member.guild, "voice", "voice_mute", embed, member)
            
        if before.deaf != after.deaf:
            action = "Server Deafened" if after.deaf else "Server Undeafened"
            icon = "🙉" if after.deaf else "👂"
            embed = discord.Embed(title=f"{icon} Voice {action}", color=0xED4245 if after.deaf else 0x57F287, description=f"{member.mention}")
            await self.send_log(member.guild, "voice", "voice_deafen", embed, member)
            
        if before.self_stream != after.self_stream:
             if after.self_stream:
                 embed = discord.Embed(title="🎥 Started Streaming", color=0x5865F2, description=f"{member.mention} in {after.channel.name}")
                 await self.send_log(member.guild, "voice", "voice_stream", embed, member)
             else:
                 embed = discord.Embed(title="⏹️ Stopped Streaming", color=0x99AAB5, description=f"{member.mention}")
                 await self.send_log(member.guild, "voice", "voice_stream", embed, member)

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


    # ==================== SERVER EVENTS ====================

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if before.description != after.description:
            changes.append("**Description:** Updated")
        if before.icon != after.icon:
            changes.append("**Icon:** Updated")
        if before.banner != after.banner:
            changes.append("**Banner:** Updated")
        if before.splash != after.splash:
            changes.append("**Splash:** Updated")
        if before.owner != after.owner:
            changes.append(f"**Owner:** {before.owner.mention} → {after.owner.mention}")
        if before.verification_level != after.verification_level:
            changes.append(f"**Verification:** {before.verification_level} → {after.verification_level}")
            
        if not changes:
            return

        embed = discord.Embed(title="🏠 Server Updated", color=0xFFA500, description="\n".join(changes))
        if after.icon:
             embed.set_thumbnail(url=after.icon.url)
        embed.set_footer(text=f"Server ID: {after.id}")
        await self.send_log(after.guild, "server", "guild_update", embed)

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild: discord.Guild):
        embed = discord.Embed(title="🧩 Integrations Updated", color=0xFFA500, description="Server integrations were updated.")
        embed.set_footer(text=f"Server ID: {guild.id}")
        await self.send_log(guild, "server", "guild_integrations_update", embed)

    # ==================== STAGE EVENTS ====================

    @commands.Cog.listener()
    async def on_stage_instance_create(self, stage_instance: discord.StageInstance):
         embed = discord.Embed(title="🎤 Stage Started", color=0x57F287, description=f"**Topic:** {stage_instance.topic}\n**Channel:** {stage_instance.channel.mention}")
         embed.set_footer(text=f"Stage ID: {stage_instance.id}")
         await self.send_log(stage_instance.guild, "stage", "stage_instance_create", embed)

    @commands.Cog.listener()
    async def on_stage_instance_delete(self, stage_instance: discord.StageInstance):
         embed = discord.Embed(title="🎤 Stage Ended", color=0xED4245, description=f"**Topic:** {stage_instance.topic}\n**Channel:** {stage_instance.channel.mention}")
         embed.set_footer(text=f"Stage ID: {stage_instance.id}")
         await self.send_log(stage_instance.guild, "stage", "stage_instance_delete", embed)

    @commands.Cog.listener()
    async def on_stage_instance_update(self, before: discord.StageInstance, after: discord.StageInstance):
         if before.topic != after.topic:
             embed = discord.Embed(title="✏️ Stage Updated", color=0xFFA500, description=f"**Channel:** {after.channel.mention}")
             embed.add_field(name="Topic Before", value=before.topic, inline=False)
             embed.add_field(name="Topic After", value=after.topic, inline=False)
             embed.set_footer(text=f"Stage ID: {after.id}")
             await self.send_log(after.guild, "stage", "stage_instance_update", embed)


async def setup(bot):
    await bot.add_cog(Logging(bot))
