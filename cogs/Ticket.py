import discord
from discord import app_commands
from discord.ext import commands

import mysql.connector
from utils.database import get_db_connection

class TicketDatabase:
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """Tables are now created via migrate_db.py or manual SQL setup. 
           This method ensures basic consistency if needed."""
        pass
    
    def get_conn(self):
        return get_db_connection()

    def set_category(self, guild_id: int, category_id: int):
        self._update_config(guild_id, "category_id", category_id)

    def set_log_channel(self, guild_id: int, channel_id: int):
        self._update_config(guild_id, "log_channel_id", channel_id)

    def set_support_role(self, guild_id: int, role_id: int):
        self._update_config(guild_id, "support_role_id", role_id)
    
    def set_panel(self, guild_id: int, channel_id: int, message_id: int):
        conn = self.get_conn()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT guild_id FROM guild_config WHERE guild_id = %s', (guild_id,))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE guild_config 
                    SET panel_channel_id = %s, panel_message_id = %s
                    WHERE guild_id = %s
                ''', (channel_id, message_id, guild_id))
            else:
                cursor.execute('''
                    INSERT INTO guild_config (guild_id, panel_channel_id, panel_message_id) 
                    VALUES (%s, %s, %s)
                ''', (guild_id, channel_id, message_id))
            conn.commit()
        finally:
            conn.close()

    def _update_config(self, guild_id: int, column: str, value: int):
        conn = self.get_conn()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT guild_id FROM guild_config WHERE guild_id = %s', (guild_id,))
            if cursor.fetchone():
                cursor.execute(f'UPDATE guild_config SET {column} = %s WHERE guild_id = %s', (value, guild_id))
            else:
                cursor.execute(f'INSERT INTO guild_config (guild_id, {column}) VALUES (%s, %s)', (guild_id, value))
            conn.commit()
        finally:
            conn.close()
    
    def get_config(self, guild_id: int):
        conn = self.get_conn()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM guild_config WHERE guild_id = %s', (guild_id,))
            result = cursor.fetchone()
            
            if result:
                # Map based on schema order: 
                # guild_id, category_id, log_channel_id, panel_channel_id, panel_message_id, support_role_id
                return {
                    'guild_id': result[0],
                    'category_id': result[1],
                    'log_channel_id': result[2],
                    'panel_channel_id': result[3],
                    'panel_message_id': result[4],
                    'support_role_id': result[5] if len(result) > 5 else None
                }
            return None
        finally:
            conn.close()
    
    def add_ticket(self, channel_id: int, guild_id: int, user_id: int, reason: str = None):
        conn = self.get_conn()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO active_tickets (channel_id, guild_id, user_id, created_at, reason)
                VALUES (%s, %s, %s, %s, %s)
            ''', (channel_id, guild_id, user_id, datetime.now().isoformat(), reason))
            conn.commit()
        finally:
            conn.close()
    
    def remove_ticket(self, channel_id: int):
        conn = self.get_conn()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM active_tickets WHERE channel_id = %s', (channel_id,))
            conn.commit()
        finally:
            conn.close()
    
    def get_user_ticket(self, guild_id: int, user_id: int):
        conn = self.get_conn()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT channel_id FROM active_tickets 
                WHERE guild_id = %s AND user_id = %s
            ''', (guild_id, user_id))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()


class TicketModal(discord.ui.Modal, title="Buat Tiket Baru"):
    reason = discord.ui.TextInput(
        label="Subjek / Alasan",
        style=discord.TextStyle.paragraph,
        placeholder="Jelaskan masalah atau pertanyaan Anda secara singkat...",
        required=True,
        max_length=500
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        cog = self.bot.get_cog('Ticket')
        if cog:
            await cog.create_ticket_for_user(interaction, self.reason.value)

class TicketControlPanel(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(
        label="Buat Tiket", 
        style=discord.ButtonStyle.green, 
        custom_id="ticket:create",
        emoji="📩"
    )
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Open Modal instead of creating ticket directly
        await interaction.response.send_modal(TicketModal(self.bot))

class TicketCloseView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(
        label="Tutup Tiket", 
        style=discord.ButtonStyle.red, 
        custom_id="ticket:close",
        emoji="🔒"
    )
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog('Ticket')
        if cog:
            await cog.close_ticket(interaction, interaction.channel)

class Ticket(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = TicketDatabase()

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Ticket Cog is ready')
        # Register persistent views
        self.bot.add_view(TicketControlPanel(self.bot))
        self.bot.add_view(TicketCloseView(self.bot))

    @app_commands.command(name="ticket-setup", description="Setup sistem tiket (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 Setup Sistem Tiket",
            description="Gunakan tombol di bawah untuk mengatur sistem tiket:",
            color=discord.Color.blue()
        )
        embed.add_field(name="📁 Set Category", value="Pilih kategori untuk channel tiket", inline=False)
        embed.add_field(name="📝 Set Log Channel", value="Pilih channel untuk log tiket", inline=False)
        embed.add_field(name="🛡️ Set Support Role", value="Pilih role yang bisa akses tiket", inline=False)
        embed.add_field(name="🎮 Send Control Panel", value="Kirim panel tiket ke channel", inline=False)
        
        view = SetupView(self.db, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def create_ticket_for_user(self, interaction: discord.Interaction, reason: str):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        author = interaction.user
        
        # Cek konfigurasi
        config = self.db.get_config(guild.id)
        if not config or not config['category_id']:
            await interaction.followup.send(embed=discord.Embed(
                title="❌ Konfigurasi Belum Lengkap",
                description="Admin belum mengatur kategori tiket. Hubungi admin server!",
                color=discord.Color.red()
            ), ephemeral=True)
            return
        
        # Cek tiket yang sudah ada
        existing_ticket_id = self.db.get_user_ticket(guild.id, author.id)
        if existing_ticket_id:
            existing_channel = guild.get_channel(existing_ticket_id)
            if existing_channel:
                await interaction.followup.send(embed=discord.Embed(
                    title="⚠️ Tiket Sudah Ada",
                    description=f"Kamu sudah memiliki tiket aktif: {existing_channel.mention}",
                    color=discord.Color.orange()
                ), ephemeral=True)
                return
            else:
                self.db.remove_ticket(existing_ticket_id)
        
        # Ambil kategori
        category = guild.get_channel(config['category_id'])
        if not category:
            await interaction.followup.send(embed=discord.Embed(
                title="❌ Kategori Tidak Ditemukan",
                description="Kategori tiket tidak valid. Hubungi admin server!",
                color=discord.Color.red()
            ), ephemeral=True)
            return
        
        # Atur permission channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                embed_links=True,
                attach_files=True
            )
        }
        
        # Tambahkan permission untuk Support Role
        if config.get('support_role_id'):
            support_role = guild.get_role(config['support_role_id'])
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True
                )

        # Tambahkan permission untuk admin (backup)
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )
        
        # Buat channel dengan kode unik
        unique_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        channel_name = f"ticket-{unique_code}"
        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Tiket bantuan untuk {author.name} (ID: {author.id})"
            )
            
            # Simpan ke database
            self.db.add_ticket(ticket_channel.id, guild.id, author.id, reason)
            
            # Embed untuk channel tiket
            ticket_embed = discord.Embed(
                title="🎟️ Tiket Baru",
                description=f"Halo {author.mention}!\nTerima kasih telah menghubungi support.",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            ticket_embed.add_field(
                name="📋 Subjek / Masalah",
                value=f"```{reason}```",
                inline=False
            )
            ticket_embed.set_footer(text=f"User ID: {author.id} • Ticket ID: {unique_code}")
            
            # Mention user and support role
            content = f"{author.mention}"
            if config.get('support_role_id'):
                content += f" <@&{config['support_role_id']}>"
            
            await ticket_channel.send(
                content=content,
                embed=ticket_embed,
                view=TicketCloseView(self.bot)
            )
            
            # Konfirmasi ke user
            await interaction.followup.send(embed=discord.Embed(
                title="✅ Tiket Berhasil Dibuat",
                description=f"Tiket kamu telah dibuat: {ticket_channel.mention}",
                color=discord.Color.green()
            ), ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                title="❌ Error",
                description=f"Terjadi kesalahan saat membuat tiket:\n```{str(e)}```",
                color=discord.Color.red()
            ), ephemeral=True)

    async def close_ticket(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # Cek permission (Admin OR Support Role)
        is_admin = interaction.user.guild_permissions.administrator
        is_support = False
        
        config = self.db.get_config(interaction.guild.id)
        if config and config.get('support_role_id'):
            support_role = interaction.guild.get_role(config['support_role_id'])
            if support_role and support_role in interaction.user.roles:
                is_support = True
        
        if not (is_admin or is_support):
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Akses Ditolak",
                description="Hanya Administrator atau Staff Support yang dapat menutup tiket.",
                color=discord.Color.red()
            ), ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Buat transcript
            messages = []
            async for message in channel.history(limit=None, oldest_first=True):
                messages.append(message)
            
            transcript = f"═══════════════════════════════════════\n"
            transcript += f"  TRANSCRIPT TIKET: {channel.name}\n"
            transcript += f"═══════════════════════════════════════\n\n"
            transcript += f"Channel: #{channel.name}\n"
            transcript += f"Ditutup oleh: {interaction.user}\n"
            transcript += f"Tanggal: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            transcript += f"\n{'='*50}\n\n"
            
            for msg in messages:
                timestamp = msg.created_at.strftime('%d/%m/%Y %H:%M:%S')
                transcript += f"[{timestamp}] {msg.author} (ID: {msg.author.id})\n"
                if msg.content:
                    transcript += f"  {msg.content}\n"
                if msg.attachments:
                    for att in msg.attachments:
                        transcript += f"  📎 {att.url}\n"
                transcript += "\n"
            
            # Simpan transcript
            filename = f"transcript_{channel.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(transcript)
            
            # Kirim ke log channel
            log_embed = discord.Embed(
                title="🔒 Tiket Ditutup",
                description=f"**Channel:** {channel.name}\n**Ditutup oleh:** {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            if config and config['log_channel_id']:
                log_channel = interaction.guild.get_channel(config['log_channel_id'])
                if log_channel:
                    try:
                        await log_channel.send(embed=log_embed, file=discord.File(filename))
                    except:
                        pass
            
            # Hapus file lokal
            try:
                os.remove(filename)
            except:
                pass
            
            # Hapus dari database
            self.db.remove_ticket(channel.id)
            
            # Kirim pesan penutupan
            close_embed = discord.Embed(
                title="🔒 Menutup Tiket",
                description="Tiket ini akan ditutup dalam 3 detik...",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=close_embed)
            
            # Delay dan hapus channel
            await asyncio.sleep(3)
            await channel.delete(reason=f"Tiket ditutup oleh {interaction.user}")
            
        except discord.NotFound:
            pass
        except Exception as e:
            try:
                await interaction.followup.send(embed=discord.Embed(
                    title="❌ Error",
                    description=f"Terjadi kesalahan:\n```{str(e)}```",
                    color=discord.Color.red()
                ), ephemeral=True)
            except:
                pass

class SetupView(discord.ui.View):
    def __init__(self, db: TicketDatabase, bot):
        super().__init__(timeout=180)
        self.db = db
        self.bot = bot
    
    @discord.ui.button(label="Set Category", style=discord.ButtonStyle.primary, emoji="📁")
    async def set_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Pilih kategori untuk tiket:", view=CategorySelect(self.db), ephemeral=True)
    
    @discord.ui.button(label="Set Log Channel", style=discord.ButtonStyle.primary, emoji="📝")
    async def set_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Pilih channel untuk log tiket:", view=LogChannelSelect(self.db), ephemeral=True)

    @discord.ui.button(label="Set Support Role", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def set_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Pilih role untuk staff support:", view=SupportRoleSelect(self.db), ephemeral=True)
    
    @discord.ui.button(label="Send Control Panel", style=discord.ButtonStyle.success, emoji="🎮")
    async def send_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Pilih channel untuk control panel:", view=PanelChannelSelect(self.db, self.bot), ephemeral=True)

class CategorySelect(discord.ui.View):
    def __init__(self, db: TicketDatabase):
        super().__init__(timeout=60)
        self.db = db
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect, 
        channel_types=[discord.ChannelType.category], 
        placeholder="Pilih kategori...",
        min_values=1, max_values=1
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        category = select.values[0]
        self.db.set_category(interaction.guild.id, category.id)
        await interaction.response.edit_message(content=None, embed=discord.Embed(title="✅ Berhasil", description=f"Kategori tiket diatur ke: **{category.name}**", color=discord.Color.green()), view=None)

class LogChannelSelect(discord.ui.View):
    def __init__(self, db: TicketDatabase):
        super().__init__(timeout=60)
        self.db = db
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect, 
        channel_types=[discord.ChannelType.text], 
        placeholder="Pilih channel log...",
        min_values=1, max_values=1
    )
    async def log_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        self.db.set_log_channel(interaction.guild.id, channel.id)
        await interaction.response.edit_message(content=None, embed=discord.Embed(title="✅ Berhasil", description=f"Log channel diatur ke: {channel.mention}", color=discord.Color.green()), view=None)

class SupportRoleSelect(discord.ui.View):
    def __init__(self, db: TicketDatabase):
        super().__init__(timeout=60)
        self.db = db
    
    @discord.ui.select(
        cls=discord.ui.RoleSelect, 
        placeholder="Pilih role support...",
        min_values=1, max_values=1
    )
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        role = select.values[0]
        self.db.set_support_role(interaction.guild.id, role.id)
        await interaction.response.edit_message(content=None, embed=discord.Embed(title="✅ Berhasil", description=f"Support role diatur ke: {role.mention}", color=discord.Color.green()), view=None)

class PanelChannelSelect(discord.ui.View):
    def __init__(self, db: TicketDatabase, bot):
        super().__init__(timeout=60)
        self.db = db
        self.bot = bot
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect, 
        channel_types=[discord.ChannelType.text], 
        placeholder="Pilih channel untuk panel...",
        min_values=1, max_values=1
    )
    async def panel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        selected_channel = select.values[0]
        channel = interaction.guild.get_channel(selected_channel.id)
        
        if not channel:
            await interaction.response.edit_message(content=None, embed=discord.Embed(title="❌ Error", description="Channel tidak ditemukan!", color=discord.Color.red()), view=None)
            return
        
        try:
            panel_embed = discord.Embed(
                title="🎫 Support Ticket",
                description="Butuh bantuan? Klik tombol di bawah untuk membuat tiket support.",
                color=discord.Color.blue()
            )
            panel_embed.set_footer(text="Support System")
            if interaction.guild.icon:
                panel_embed.set_thumbnail(url=interaction.guild.icon.url)
            
            panel_message = await channel.send(embed=panel_embed, view=TicketControlPanel(self.bot))
            self.db.set_panel(interaction.guild.id, channel.id, panel_message.id)
            
            await interaction.response.edit_message(content=None, embed=discord.Embed(title="✅ Berhasil", description=f"Control panel berhasil dikirim ke {channel.mention}!\n\n[Klik di sini untuk melihat]({panel_message.jump_url})", color=discord.Color.green()), view=None)
            
        except discord.Forbidden:
            await interaction.response.edit_message(content=None, embed=discord.Embed(title="❌ Error", description=f"Bot tidak memiliki permission untuk mengirim pesan di {channel.mention}", color=discord.Color.red()), view=None)
        except Exception as e:
            await interaction.response.edit_message(content=None, embed=discord.Embed(title="❌ Error", description=f"Terjadi kesalahan:\n```{str(e)}```", color=discord.Color.red()), view=None)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
