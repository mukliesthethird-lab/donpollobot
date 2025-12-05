import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import sqlite3
import aiosqlite
import os

class ConfirmClearView(discord.ui.View):
    def __init__(self, member, total_warnings):
        super().__init__(timeout=60)
        self.member = member
        self.total_warnings = total_warnings
        self.value = None

    @discord.ui.button(label='✅ Ya, Hapus Semua', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        
        # Hapus semua warnings dari database
        warn_cog = interaction.client.get_cog('Warn')
        await warn_cog.clear_user_warnings(interaction.guild.id, self.member.id)
        
        # Embed konfirmasi
        embed = discord.Embed(
            title="✅ Warnings Berhasil Dihapus",
            description=f"Semua **{self.total_warnings}** peringatan untuk {self.member.mention} telah dihapus.",
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(
            text=f"Dihapus oleh {interaction.user.display_name}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        
        if self.member.avatar:
            embed.set_thumbnail(url=self.member.avatar.url)
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label='❌ Batal', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        
        embed = discord.Embed(
            title="❌ Dibatalkan",
            description="Penghapusan warnings dibatalkan.",
            color=0x808080
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class Warn(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.db_path = "database.db"
        
    async def init_database(self):
        """Inisialisasi database dan tabel"""
        async with aiosqlite.connect(self.db_path) as db:
            # Cek apakah tabel warnings sudah ada
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='warnings'")
            table_exists = await cursor.fetchone()
            
            if not table_exists:
                # Buat tabel baru dengan struktur lengkap
                await db.execute('''
                    CREATE TABLE warnings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        moderator_id INTEGER NOT NULL,
                        moderator_name TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        case_number INTEGER NOT NULL
                    )
                ''')
            else:
                # Cek apakah kolom moderator_name sudah ada
                cursor = await db.execute("PRAGMA table_info(warnings)")
                columns = await cursor.fetchall()
                column_names = [column[1] for column in columns]
                
                if 'moderator_name' not in column_names:
                    # Tambahkan kolom moderator_name jika belum ada
                    await db.execute('ALTER TABLE warnings ADD COLUMN moderator_name TEXT DEFAULT "Unknown Moderator"')
                    print("✅ Added moderator_name column to existing warnings table")
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS warn_cases (
                    guild_id INTEGER PRIMARY KEY,
                    current_case INTEGER DEFAULT 0
                )
            ''')
            
            await db.commit()
    
    async def get_next_case_number(self, guild_id):
        """Mendapatkan nomor kasus berikutnya untuk guild"""
        async with aiosqlite.connect(self.db_path) as db:
            # Cek apakah guild sudah ada
            async with db.execute('SELECT current_case FROM warn_cases WHERE guild_id = ?', (guild_id,)) as cursor:
                row = await cursor.fetchone()
                
            if row:
                new_case = row[0] + 1
                await db.execute('UPDATE warn_cases SET current_case = ? WHERE guild_id = ?', (new_case, guild_id))
            else:
                new_case = 1
                await db.execute('INSERT INTO warn_cases (guild_id, current_case) VALUES (?, ?)', (guild_id, new_case))
            
            await db.commit()
            return new_case
    
    async def add_warning(self, guild_id, user_id, moderator_id, moderator_name, reason, case_number):
        """Menambahkan warning ke database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO warnings (guild_id, user_id, moderator_id, moderator_name, reason, case_number)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (guild_id, user_id, moderator_id, moderator_name, reason, case_number))
            await db.commit()
    
    async def get_user_warnings(self, guild_id, user_id):
        """Mendapatkan semua warning untuk user tertentu"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT * FROM warnings 
                WHERE guild_id = ? AND user_id = ?
                ORDER BY timestamp DESC
            ''', (guild_id, user_id)) as cursor:
                return await cursor.fetchall()
    
    async def clear_user_warnings(self, guild_id, user_id):
        """Menghapus semua warning untuk user tertentu"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                DELETE FROM warnings 
                WHERE guild_id = ? AND user_id = ?
            ''', (guild_id, user_id))
            await db.commit()

    def is_admin(self, member):
        """Cek apakah member adalah admin"""
        return member.guild_permissions.administrator

    @commands.Cog.listener()
    async def on_ready(self):
        await self.init_database()
        print('✅ Warn Cog is ready with database connection')

    @app_commands.command(name="warn", description="Memberikan peringatan kepada anggota (Admin Only)")
    @app_commands.describe(member="Member yang akan diperingatkan", reason="Alasan peringatan")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        # Cek permission admin
        if not self.is_admin(interaction.user):
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Kamu tidak memiliki izin untuk menggunakan command ini.\nHanya **Administrator** yang dapat memberikan peringatan.",
                color=0xFF0000
            )
            embed.set_footer(text="Diperlukan: Administrator Permission")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Cek apakah user mencoba warn dirinya sendiri
        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="❌ Error",
                description="Kamu tidak bisa memberikan peringatan kepada diri sendiri!",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Cek apakah user mencoba warn bot
        if member.bot:
            embed = discord.Embed(
                title="❌ Error", 
                description="Kamu tidak bisa memberikan peringatan kepada bot!",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Cek apakah target adalah admin
        if self.is_admin(member):
            embed = discord.Embed(
                title="❌ Error",
                description="Kamu tidak bisa memberikan peringatan kepada Administrator!",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild_id = interaction.guild.id
        user_id = member.id

        try:
            # Mendapatkan nomor kasus berikutnya
            case_number = await self.get_next_case_number(guild_id)
            
            # Menambahkan warning ke database dengan nama moderator
            await self.add_warning(guild_id, user_id, interaction.user.id, interaction.user.display_name, reason, case_number)
            
            # Mendapatkan total warnings user
            warnings = await self.get_user_warnings(guild_id, user_id)
            total_warnings = len(warnings)
            
            # Waktu saat ini dalam format yang lebih bagus
            current_time = datetime.utcnow()
            time_formatted = current_time.strftime("%d %B %Y, %H:%M UTC")
            
            # Embed untuk DM ke user yang diwarn
            dm_embed = discord.Embed(
                title="⚠️ Peringatan Diterima",
                description=f"Kamu telah menerima peringatan di server **{interaction.guild.name}**",
                color=0xFFA500,
                timestamp=current_time
            )
            dm_embed.add_field(
                name="👮 Moderator", 
                value=f"{interaction.user.display_name}", 
                inline=True
            )
            dm_embed.add_field(
                name="📋 Kasus #", 
                value=f"`{case_number:04d}`", 
                inline=True
            )
            dm_embed.add_field(
                name="📊 Total Warnings", 
                value=f"`{total_warnings}`", 
                inline=True
            )
            dm_embed.add_field(
                name="📝 Alasan", 
                value=f"```{reason}```", 
                inline=False
            )
            
            if interaction.guild.icon:
                dm_embed.set_thumbnail(url=interaction.guild.icon.url)
            
            dm_embed.set_footer(
                text=f"Server: {interaction.guild.name}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            # Coba kirim DM ke user
            dm_sent = False
            try:
                await member.send(embed=dm_embed)
                dm_sent = True
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
            
            # Embed response di channel
            response_embed = discord.Embed(
                title="✅ Peringatan Berhasil Diberikan",
                color=0x00FF00,
                timestamp=current_time
            )
            
            response_embed.add_field(
                name="🎯 Target",
                value=f"{member.mention}\n`{member.display_name}`",
                inline=True
            )
            response_embed.add_field(
                name="👮 Moderator", 
                value=f"{interaction.user.mention}\n`{interaction.user.display_name}`",
                inline=True
            )
            response_embed.add_field(
                name="📋 Kasus #",
                value=f"`{case_number:04d}`",
                inline=True
            )
            response_embed.add_field(
                name="📝 Alasan",
                value=f"```{reason}```",
                inline=False
            )
            response_embed.add_field(
                name="📊 Status",
                value=f"**Total Warnings:** `{total_warnings}`\n**DM Terkirim:** {'✅ Ya' if dm_sent else '❌ Tidak'}",
                inline=True
            )
            response_embed.add_field(
                name="⏰ Waktu",
                value=f"`{time_formatted}`",
                inline=True
            )
            
            if member.avatar:
                response_embed.set_thumbnail(url=member.avatar.url)
            
            response_embed.set_footer(
                text=f"Dieksekusi oleh {interaction.user.display_name}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            # Dispatch event untuk logging lainnya jika diperlukan
            self.client.dispatch('warn_add', member, interaction.user, reason, case_number)
            
            await interaction.response.send_message(embed=response_embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Terjadi Kesalahan",
                description="Terjadi kesalahan saat memproses peringatan.",
                color=0xFF0000
            )
            error_embed.add_field(
                name="Error Details",
                value=f"```{str(e)}```",
                inline=False
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            print(f"Error in warn command: {e}")

    @app_commands.command(name="warnings", description="Melihat daftar peringatan seorang member (Admin Only)")
    @app_commands.describe(member="Member yang ingin dilihat peringatannya")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        # Cek permission admin
        if not self.is_admin(interaction.user):
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Kamu tidak memiliki izin untuk menggunakan command ini.\nHanya **Administrator** yang dapat melihat peringatan.",
                color=0xFF0000
            )
            embed.set_footer(text="Diperlukan: Administrator Permission")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        if member is None:
            member = interaction.user
        
        guild_id = interaction.guild.id
        user_id = member.id
        
        try:
            warnings = await self.get_user_warnings(guild_id, user_id)
            
            if not warnings:
                embed = discord.Embed(
                    title="📊 Riwayat Peringatan",
                    description=f"**{member.display_name}** belum memiliki peringatan di server ini.",
                    color=0x00FF00
                )
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
            else:
                embed = discord.Embed(
                    title="📊 Riwayat Peringatan",
                    description=f"**{member.display_name}** memiliki **{len(warnings)}** peringatan",
                    color=0xFF0000 if len(warnings) >= 3 else 0xFFA500
                )
                
                # Tampilkan maksimal 5 warning terakhir
                for i, warning in enumerate(warnings[:5]):
                    # Gunakan moderator_name dari database (kolom ke-4, index 4)
                    moderator_name = warning[4]  # moderator_name dari database
                    
                    warning_time = datetime.fromisoformat(warning[6].replace('Z', '+00:00'))
                    time_formatted = warning_time.strftime("%d/%m/%Y %H:%M")
                    
                    embed.add_field(
                        name=f"⚠️ Kasus #{warning[7]:04d}",  # case_number adalah kolom ke-7
                        value=f"**Moderator:** {moderator_name}\n**Alasan:** {warning[5]}\n**Waktu:** {time_formatted}",
                        inline=False
                    )
                
                if len(warnings) > 5:
                    embed.add_field(
                        name="📝 Catatan",
                        value=f"Menampilkan 5 peringatan terbaru dari total {len(warnings)} peringatan.",
                        inline=False
                    )
                
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
            
            embed.set_footer(
                text=f"Diminta oleh {interaction.user.display_name}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            # Tambahkan tombol Clear Warnings jika ada warnings
            view = None
            if warnings:
                view = ClearWarningsView(member, len(warnings))
            
            await interaction.response.send_message(embed=embed, view=view)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Terjadi Kesalahan",
                description="Terjadi kesalahan saat mengambil data peringatan.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            print(f"Error in warnings command: {e}")

class ClearWarningsView(discord.ui.View):
    def __init__(self, member, total_warnings):
        super().__init__(timeout=300)  # 5 menit timeout
        self.member = member
        self.total_warnings = total_warnings

    @discord.ui.button(label='🗑️ Clear All Warnings', style=discord.ButtonStyle.danger)
    async def clear_warnings(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Cek apakah user yang menekan tombol adalah admin
        warn_cog = interaction.client.get_cog('Warn')
        if not warn_cog.is_admin(interaction.user):
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Hanya Administrator yang dapat menghapus peringatan.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Konfirmasi penghapusan
        confirm_embed = discord.Embed(
            title="⚠️ Konfirmasi Penghapusan",
            description=f"Apakah kamu yakin ingin menghapus **semua {self.total_warnings} peringatan** untuk {self.member.mention}?\n\n**Tindakan ini tidak dapat dibatalkan!**",
            color=0xFFA500
        )
        confirm_embed.set_footer(text="Konfirmasi akan timeout dalam 60 detik")
        
        if self.member.avatar:
            confirm_embed.set_thumbnail(url=self.member.avatar.url)
        
        view = ConfirmClearView(self.member, self.total_warnings)
        await interaction.response.edit_message(embed=confirm_embed, view=view)

    async def on_timeout(self):
        # Nonaktifkan semua button ketika timeout
        for item in self.children:
            item.disabled = True

async def setup(client):
    await client.add_cog(Warn(client))
# Maintenance update
