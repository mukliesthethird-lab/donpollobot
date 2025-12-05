import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from datetime import datetime
import asyncio

class TicketDatabase:
    def __init__(self, db_name="database.db"):
        self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Tabel untuk konfigurasi guild
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                category_id INTEGER,
                log_channel_id INTEGER,
                panel_channel_id INTEGER,
                panel_message_id INTEGER
            )
        ''')
        
        # Tabel untuk tracking tiket aktif
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_tickets (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                user_id INTEGER,
                created_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def set_category(self, guild_id: int, category_id: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO guild_config (guild_id, category_id) 
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET category_id = ?
        ''', (guild_id, category_id, category_id))
        conn.commit()
        conn.close()
    
    def set_log_channel(self, guild_id: int, channel_id: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO guild_config (guild_id, log_channel_id) 
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET log_channel_id = ?
        ''', (guild_id, channel_id, channel_id))
        conn.commit()
        conn.close()
    
    def set_panel(self, guild_id: int, channel_id: int, message_id: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO guild_config (guild_id, panel_channel_id, panel_message_id) 
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                panel_channel_id = ?,
                panel_message_id = ?
        ''', (guild_id, channel_id, message_id, channel_id, message_id))
        conn.commit()
        conn.close()
    
    def get_config(self, guild_id: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM guild_config WHERE guild_id = ?', (guild_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'guild_id': result[0],
                'category_id': result[1],
                'log_channel_id': result[2],
                'panel_channel_id': result[3],
                'panel_message_id': result[4]
            }
        return None
    
    def add_ticket(self, channel_id: int, guild_id: int, user_id: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO active_tickets (channel_id, guild_id, user_id, created_at)
            VALUES (?, ?, ?, ?)
        ''', (channel_id, guild_id, user_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def remove_ticket(self, channel_id: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM active_tickets WHERE channel_id = ?', (channel_id,))
        conn.commit()
        conn.close()
    
    def get_user_ticket(self, guild_id: int, user_id: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT channel_id FROM active_tickets 
            WHERE guild_id = ? AND user_id = ?
        ''', (guild_id, user_id))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

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
        cog = self.bot.get_cog('Ticket')
        if cog:
            await cog.create_ticket_for_user(interaction)

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
        embed.add_field(
            name="📁 Set Category",
            value="Pilih kategori untuk channel tiket",
            inline=False
        )
        embed.add_field(
            name="📝 Set Log Channel",
            value="Pilih channel untuk log tiket yang ditutup",
            inline=False
        )
        embed.add_field(
            name="🎮 Send Control Panel",
            value="Kirim panel untuk user membuat tiket",
            inline=False
        )
        
        view = SetupView(self.db, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def create_ticket_for_user(self, interaction: discord.Interaction):
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
                # Channel sudah terhapus, bersihkan database
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
        
        # Tambahkan permission untuk admin
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )
        
        # Buat channel dengan kode unik
        import random
        import string
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
            self.db.add_ticket(ticket_channel.id, guild.id, author.id)
            
            # Embed untuk channel tiket
            ticket_embed = discord.Embed(
                title="🎟️ Tiket Dibuka",
                description=f"Halo {author.mention}!\n\nSilakan sampaikan pertanyaan atau masalahmu di sini.\nTim support kami akan segera membantu.",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            ticket_embed.add_field(
                name="📌 Informasi",
                value="• Jelaskan masalahmu dengan detail\n• Tunggu respon dari staff\n• Admin dapat menutup tiket dengan tombol di bawah",
                inline=False
            )
            ticket_embed.set_footer(text=f"User ID: {author.id}")
            
            await ticket_channel.send(
                content=author.mention,
                embed=ticket_embed,
                view=TicketCloseView(self.bot)
            )
            
            # Konfirmasi ke user
            await interaction.followup.send(embed=discord.Embed(
                title="✅ Tiket Berhasil Dibuat",
                description=f"Tiket kamu telah dibuat: {ticket_channel.mention}\n\nSilakan jelaskan masalahmu di sana!",
                color=discord.Color.green()
            ), ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                title="❌ Error",
                description=f"Terjadi kesalahan saat membuat tiket:\n```{str(e)}```",
                color=discord.Color.red()
            ), ephemeral=True)

    async def close_ticket(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # Cek permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Akses Ditolak",
                description="Hanya administrator yang dapat menutup tiket.",
                color=discord.Color.red()
            ), ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Ambil konfigurasi untuk log channel
            config = self.db.get_config(interaction.guild.id)
            
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
            pass  # Channel sudah dihapus
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
        await interaction.response.send_message(
            "Pilih kategori untuk tiket:",
            view=CategorySelect(self.db),
            ephemeral=True
        )
    
    @discord.ui.button(label="Set Log Channel", style=discord.ButtonStyle.primary, emoji="📝")
    async def set_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Pilih channel untuk log tiket:",
            view=LogChannelSelect(self.db),
            ephemeral=True
        )
    
    @discord.ui.button(label="Send Control Panel", style=discord.ButtonStyle.success, emoji="🎮")
    async def send_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Pilih channel untuk control panel:",
            view=PanelChannelSelect(self.db, self.bot),
            ephemeral=True
        )

class CategorySelect(discord.ui.View):
    def __init__(self, db: TicketDatabase):
        super().__init__(timeout=60)
        self.db = db
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect, 
        channel_types=[discord.ChannelType.category], 
        placeholder="Pilih kategori...",
        min_values=1,
        max_values=1
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        category = select.values[0]
        self.db.set_category(interaction.guild.id, category.id)
        
        embed = discord.Embed(
            title="✅ Berhasil",
            description=f"Kategori tiket diatur ke: **{category.name}**",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )

class LogChannelSelect(discord.ui.View):
    def __init__(self, db: TicketDatabase):
        super().__init__(timeout=60)
        self.db = db
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect, 
        channel_types=[discord.ChannelType.text], 
        placeholder="Pilih channel log...",
        min_values=1,
        max_values=1
    )
    async def log_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        self.db.set_log_channel(interaction.guild.id, channel.id)
        
        embed = discord.Embed(
            title="✅ Berhasil",
            description=f"Log channel diatur ke: {channel.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )

class PanelChannelSelect(discord.ui.View):
    def __init__(self, db: TicketDatabase, bot):
        super().__init__(timeout=60)
        self.db = db
        self.bot = bot
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect, 
        channel_types=[discord.ChannelType.text], 
        placeholder="Pilih channel untuk panel...",
        min_values=1,
        max_values=1
    )
    async def panel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        selected_channel = select.values[0]
        
        # Ambil channel yang sebenarnya dari guild
        channel = interaction.guild.get_channel(selected_channel.id)
        
        if not channel:
            error_embed = discord.Embed(
                title="❌ Error",
                description="Channel tidak ditemukan!",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(
                content=None,
                embed=error_embed,
                view=None
            )
            return
        
        try:
            # Buat control panel embed
            panel_embed = discord.Embed(
                title="🎫 Support Ticket",
                description="Butuh bantuan? Klik tombol di bawah untuk membuat tiket support.",
                color=discord.Color.blue()
            )
            panel_embed.set_footer(text="Support System")
            
            if interaction.guild.icon:
                panel_embed.set_thumbnail(url=interaction.guild.icon.url)
            
            # Kirim panel ke channel yang dipilih
            panel_message = await channel.send(
                embed=panel_embed, 
                view=TicketControlPanel(self.bot)
            )
            
            # Simpan ke database
            self.db.set_panel(interaction.guild.id, channel.id, panel_message.id)
            
            success_embed = discord.Embed(
                title="✅ Berhasil",
                description=f"Control panel berhasil dikirim ke {channel.mention}!\n\n[Klik di sini untuk melihat]({panel_message.jump_url})",
                color=discord.Color.green()
            )
            
            await interaction.response.edit_message(
                content=None,
                embed=success_embed,
                view=None
            )
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Bot tidak memiliki permission untuk mengirim pesan di {channel.mention}",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(
                content=None,
                embed=error_embed,
                view=None
            )
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Terjadi kesalahan:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(
                content=None,
                embed=error_embed,
                view=None
            )

async def setup(bot):
    await bot.add_cog(Ticket(bot))
# Maintenance update
