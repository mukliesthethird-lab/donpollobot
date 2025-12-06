import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
from datetime import datetime, timedelta
from typing import Optional
import aiohttp
from utils.database import get_db_connection

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._init_db()

    def get_conn(self):
        return get_db_connection()

    def _init_db(self):
        """Initialize the economy table (using existing slot_users table)"""
        conn = self.get_conn()
        if not conn:
            print("❌ Failed to connect to DB in Economy init")
            return
            
        cursor = conn.cursor()
        # We use the existing slot_users table as the main economy table
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS slot_users (
                    user_id BIGINT PRIMARY KEY,
                    balance BIGINT DEFAULT 500,
                    total_wins INT DEFAULT 0,
                    total_losses INT DEFAULT 0,
                    last_daily TEXT,
                    last_work TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Loans table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS loans (
                    user_id BIGINT PRIMARY KEY,
                    amount BIGINT,
                    due_date TEXT
                )
            ''')
            conn.commit()
        except Exception as e:
            print(f"Error initializing Economy DB: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Economy Cog is ready')
        self.check_loans.start()

    @tasks.loop(minutes=1)
    async def check_loans(self):
        """Background task to check for due loans"""
        conn = self.get_conn()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            now = datetime.now()
            
            # Get due loans
            cursor.execute('SELECT user_id, amount, due_date FROM loans')
            loans = cursor.fetchall()
            
            for uid, amount, due_date_str in loans:
                try:
                    due_date = datetime.fromisoformat(due_date_str)
                    if now >= due_date:
                        # Loan is due! Deduct balance
                        self.update_balance(uid, -amount)
                        
                        # Remove from loans table
                        cursor.execute('DELETE FROM loans WHERE user_id = %s', (uid,))
                        conn.commit()
                        
                        print(f"[LOAN] Auto-deducted {amount} from {uid}")
                except Exception as e:
                    print(f"[LOAN ERROR] {e}")
        except Exception as e:
            print(f"Error in check_loans: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_user_data(self, user_id: int):
        """Get user data from database"""
        conn = self.get_conn()
        if not conn: return 500, 0, 0, None, None
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT balance, total_wins, total_losses, last_daily, last_work FROM slot_users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                # Create new user with starting balance
                cursor.execute('''
                    INSERT INTO slot_users (user_id, balance, total_wins, total_losses)
                    VALUES (%s, 500, 0, 0)
                ''', (user_id,))
                conn.commit()
                return 500, 0, 0, None, None
            
            return result
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_balance(self, user_id: int) -> int:
        """Get user balance"""
        # Optimized: Don't call get_user_data which opens another connection
        conn = self.get_conn()
        if not conn: return 0
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT balance FROM slot_users WHERE user_id = %s', (user_id,))
            res = cursor.fetchone()
            if res:
                return res[0]
            else:
                # Initialize
                self.get_user_data(user_id) 
                return 500
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    def update_balance(self, user_id: int, amount: int) -> int:
        """Update user balance. Returns new balance."""
        
        # Ensure user exists (this creates it if not)
        # We can optimize by trying UPDATE first, if affected_rows == 0 then INSERT.
        # But sticking to existing logic flow for safety:
        self.get_user_data(user_id)
        
        conn = self.get_conn()
        if not conn: return 0
        
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE slot_users SET balance = balance + %s WHERE user_id = %s', (amount, user_id))
            conn.commit()
            
            # Fetch new balance
            cursor.execute('SELECT balance FROM slot_users WHERE user_id = %s', (user_id,))
            res = cursor.fetchone()
            return res[0] if res else 0
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def transfer_money(self, sender_id: int, receiver_id: int, amount: int) -> bool:
        """Transfer money between users. Returns True if successful."""
        if amount <= 0: return False
            
        sender_bal = self.get_balance(sender_id)
        if sender_bal < amount: return False
            
        # Ensure receiver exists
        self.get_user_data(receiver_id)
        
        conn = self.get_conn()
        if not conn: return False
        
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE slot_users SET balance = balance - %s WHERE user_id = %s', (amount, sender_id))
            cursor.execute('UPDATE slot_users SET balance = balance + %s WHERE user_id = %s', (amount, receiver_id))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @app_commands.command(name="balance", description="Cek saldo koin Anda")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        if target.bot:
            await interaction.response.send_message("❌ Bot tidak memiliki saldo!", ephemeral=True)
            return

        balance = self.get_balance(target.id)
        
        embed = discord.Embed(
            title=f"💰 Saldo {target.display_name}",
            description=f"**{balance:,}** koin",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pay", description="Transfer koin ke user lain")
    @app_commands.describe(user="User tujuan", amount="Jumlah koin")
    async def pay(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ Anda tidak bisa transfer ke diri sendiri!", ephemeral=True)
            return
            
        if user.bot:
            await interaction.response.send_message("❌ Anda tidak bisa transfer ke bot!", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Jumlah harus lebih dari 0!", ephemeral=True)
            return

        if self.transfer_money(interaction.user.id, user.id, amount):
            embed = discord.Embed(
                title="💸 Transfer Berhasil",
                description=f"Anda berhasil mentransfer **{amount:,}** koin ke {user.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Saldo tidak cukup!", ephemeral=True)

    @app_commands.command(name="daily", description="Klaim bonus harian (setiap 24 jam)")
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        _, _, _, last_daily, _ = self.get_user_data(user_id)
        
        now = datetime.now()
        
        if last_daily:
            try:
                last_claim = datetime.fromisoformat(last_daily)
                if now - last_claim < timedelta(days=1):
                    next_claim = last_claim + timedelta(days=1)
                    time_left = next_claim - now
                    hours = int(time_left.total_seconds() // 3600)
                    minutes = int((time_left.total_seconds() % 3600) // 60)
                    
                    await interaction.response.send_message(
                        f"⏰ Tunggu **{hours} jam {minutes} menit** lagi untuk klaim daily!", 
                        ephemeral=True
                    )
                    return
            except ValueError:
                pass # Invalid date format, allow claim

        reward = 200
        self.update_balance(user_id, reward)
        
        conn = self.get_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('UPDATE slot_users SET last_daily = %s WHERE user_id = %s', (now.isoformat(), user_id))
                conn.commit()
            finally:
                if conn.is_connected():
                    cursor.close()
                    conn.close()
        
        embed = discord.Embed(
            title="🌞 Daily Reward",
            description=f"Kamu mendapatkan **{reward}** koin!\nSaldo sekarang: **{self.get_balance(user_id):,}** koin",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Bekerja untuk mendapatkan koin (setiap 1 jam)")
    async def work(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        _, _, _, _, last_work = self.get_user_data(user_id)
        
        now = datetime.now()
        
        if last_work:
            try:
                last_work_time = datetime.fromisoformat(last_work)
                if now - last_work_time < timedelta(hours=1):
                    next_work = last_work_time + timedelta(hours=1)
                    time_left = next_work - now
                    minutes = int(time_left.total_seconds() // 60)
                    
                    await interaction.response.send_message(
                        f"⏰ Kamu sedang lelah! Tunggu **{minutes} menit** lagi.", 
                        ephemeral=True
                    )
                    return
            except ValueError:
                pass

        earnings = random.randint(50, 350)
        self.update_balance(user_id, earnings)
        
        conn = self.get_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('UPDATE slot_users SET last_work = %s WHERE user_id = %s', (now.isoformat(), user_id))
                conn.commit()
            finally:
                if conn.is_connected():
                    cursor.close()
                    conn.close()
        
        jobs = ["Barista", "Programmer", "Gamer", "Chef", "Driver", "Artist", "Editor", "Slave", "Mechanic"]
        job = random.choice(jobs)
        
        embed = discord.Embed(
            title="💼 Kerja Keras",
            description=f"Kamu bekerja sebagai **{job}** dan mendapat **{earnings}** koin!\nSaldo sekarang: **{self.get_balance(user_id):,}** koin",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)



    @app_commands.command(name="remove_money", description="[OWNER] Kurangi koin user")
    @app_commands.describe(amount="Jumlah koin", user="User tujuan")
    async def remove_money(self, interaction: discord.Interaction, amount: int, user: discord.Member):
        # Restricted to specific user ID
        if interaction.user.id != 719511161757761656:
            await interaction.response.send_message("❌ Kamu tidak memiliki akses ke command ini!", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Jumlah harus lebih dari 0!", ephemeral=True)
            return

        new_balance = self.update_balance(user.id, -amount)
        
        embed = discord.Embed(
            title="💸 Remove Money",
            description=f"Berhasil mengurangi **{amount:,}** koin dari {user.mention}.\nSaldo sekarang: **{new_balance:,}**",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ngutang", description="Pinjam koin (Jatuh tempo 24 jam)")
    @app_commands.describe(amount="Jumlah pinjaman (Max 15000)")
    async def ngutang(self, interaction: discord.Interaction, amount: int):
        user_id = interaction.user.id
        
        if amount <= 0 or amount > 15000:
            await interaction.response.send_message("❌ Jumlah pinjaman harus 1 - 15000 koin!", ephemeral=True)
            return

        conn = self.get_conn()
        if not conn:
             await interaction.response.send_message("❌ Database Error", ephemeral=True)
             return
             
        try:
            cursor = conn.cursor()
            
            # Check if already has loan (Fast check)
            cursor.execute('SELECT amount FROM loans WHERE user_id = %s', (user_id,))
            if cursor.fetchone():
                await interaction.response.send_message("❌ **Bayar dulu hutang sebelumnya!**\nLunasi hutang lama baru bisa pinjam lagi.", ephemeral=True)
                return

            due_date = datetime.now() + timedelta(days=1)
            
            try:
                # Try to insert loan first (Atomic check via Primary Key)
                cursor.execute('INSERT INTO loans (user_id, amount, due_date) VALUES (%s, %s, %s)', 
                               (user_id, amount, due_date.isoformat()))
                conn.commit()
                
                # If successful, give money
                self.update_balance(user_id, amount)
                
                embed = discord.Embed(
                    title="💸 Pinjaman Berhasil",
                    description=f"Anda meminjam **{amount:,}** koin.\n\n⚠️ **Jatuh Tempo:** <t:{int(due_date.timestamp())}:R>\nJika telat, saldo akan otomatis terpotong (bisa minus).",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                
            except mysql.connector.IntegrityError:
                # Race condition caught: User already has a loan
                await interaction.response.send_message("❌ **Bayar dulu hutang sebelumnya!**", ephemeral=True)
            except Exception as e:
                print(f"Error in ngutang: {e}")
                await interaction.response.send_message("❌ Terjadi kesalahan saat memproses pinjaman.", ephemeral=True)
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @app_commands.command(name="pay_loan", description="Bayar hutang lebih awal")
    async def pay_loan(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = self.get_conn()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('SELECT amount FROM loans WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                await interaction.response.send_message("✅ Anda tidak memiliki hutang!", ephemeral=True)
                return
                
            amount = result[0]
            balance = self.get_balance(user_id)
            
            if balance < amount:
                await interaction.response.send_message(f"❌ Saldo tidak cukup untuk bayar hutang! (Butuh: {amount}, Ada: {balance})", ephemeral=True)
                return
                
            # Pay loan
            self.update_balance(user_id, -amount)
            cursor.execute('DELETE FROM loans WHERE user_id = %s', (user_id,))
            conn.commit()
            
            await interaction.response.send_message(f"✅ Hutang sebesar **{amount:,}** koin telah lunas!", ephemeral=True)
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    # =========================================================================
    # UNIFIED LEADERBOARD (RAW PAYLOAD IMPLEMENTATION)
    # =========================================================================

    @app_commands.command(name="leaderboard", description="Lihat leaderboard server (Ekonomi & Fishing)")
    async def leaderboard(self, interaction: discord.Interaction):
        # Initial payload for leaderboard
        payload = self.build_leaderboard_payload("initial")
        await self.send_raw_payload(interaction, payload)

    async def send_raw_payload(self, interaction: discord.Interaction, payload: dict):
        url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        json_payload = {"type": 4, "data": payload}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json_payload, headers=headers) as resp:
                if resp.status not in [200, 204]:
                    print(f"❌ Error sending Leaderboard payload: {resp.status} {await resp.text()}")

    async def update_raw_message(self, interaction: discord.Interaction, payload: dict):
        url = f"https://discord.com/api/v10/webhooks/{self.bot.user.id}/{interaction.token}/messages/@original"
        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        
        # Type 7: Update Message
        json_payload = {"type": 7, "data": payload}
        
        callback_url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
        async with aiohttp.ClientSession() as session:
            async with session.post(callback_url, json=json_payload, headers=headers) as resp:
                    if resp.status != 200:
                        print(f"Error updating message: {await resp.text()}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id")
            
            if custom_id == "unified_leaderboard_select":
                selected = interaction.data["values"][0]
                payload = self.build_leaderboard_payload(selected)
                await self.update_raw_message(interaction, payload)

    def build_leaderboard_payload(self, selected_value):
        # Determine content based on selection
        content_text = ""
        
        if selected_value == "initial":
            content_text = "## Silakan pilih kategori leaderboard di bawah ini."
            
        elif selected_value == "economy_balance":
            conn = self.get_conn()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id, balance FROM slot_users ORDER BY balance DESC LIMIT 10')
                    top_users = cursor.fetchall()
                    
                    content_text = "## 💰 Global Rich List (Economy)\n\n"
                    if not top_users:
                        content_text += "*Belum ada data.*"
                    else:
                        for i, (uid, bal) in enumerate(top_users, 1):
                            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                            user = self.bot.get_user(uid)
                            name = user.name if user else f"User {uid}"
                            content_text += f"{medal} **{name}** - {bal:,} koin\n"
                finally:
                    if conn.is_connected():
                        cursor.close()
                        conn.close()

        elif selected_value.startswith("fish_"):
            fishing_cog = self.bot.get_cog("Fishing")
            if not fishing_cog:
                content_text = "❌ Fishing cog not loaded!"
            else:
                if selected_value == "fish_networth":
                    data = fishing_cog.get_networth_leaderboard()
                    content_text = "## 🐟 Fishing Networth Leaderboard\n\n"
                    if not data:
                        content_text += "*Belum ada data.*"
                    else:
                        for i, row in enumerate(data, start=1):
                            user_id = row[0]
                            user = self.bot.get_user(user_id)
                            username = user.name if user else f"User {user_id}"
                            total_value = row[1]
                            content_text += f"**{i}. {username}** - 💰 {total_value:,}\n"

                elif selected_value == "fish_weight":
                    data = fishing_cog.get_weight_leaderboard()
                    content_text = "## 🏆 Leaderboard Berat Ikan\n\n"
                    if not data:
                        content_text += "*Belum ada data.*"
                    else:
                        for i, row in enumerate(data, start=1):
                            user_id = row[0]
                            user = self.bot.get_user(user_id)
                            username = user.name if user else f"User {user_id}"
                            fish_name, weight, rarity = row[1], row[2], row[3]
                            content_text += f"**{i}. {username}** - {fish_name} ({weight}kg) `{rarity}`\n"

                elif selected_value == "fish_catch":
                    data = fishing_cog.get_top_fisher_leaderboard()
                    content_text = "## 🎣 Top Fisher Leaderboard\n\n"
                    if not data:
                        content_text += "*Belum ada data.*"
                    else:
                        for i, row in enumerate(data, start=1):
                            user_id = row[0]
                            user = self.bot.get_user(user_id)
                            username = user.name if user else f"User {user_id}"
                            total_catches = row[1]
                            content_text += f"**{i}. {username}** - 🎣 {total_catches} catches\n"
        
        # Construct the JSON Payload
        return {
            "flags": 32768, # Special flag for V2 components
            "components": [
                {
                    "type": 17, # Container
                    "components": [
                        {
                            "type": 10, # Text Display
                            "content": "# 🏆 SERVER LEADERBOARD"
                        },
                        {
                            "type": 14, # Spacer
                            "spacing": 1
                        },
                        {
                            "type": 1, # Action Row
                            "components": [
                                {
                                    "type": 3, # Select Menu
                                    "custom_id": "unified_leaderboard_select",
                                    "options": [
                                        {
                                            "label": "Top Balance (Economy)",
                                            "value": "economy_balance",
                                            "description": "Orang terkaya di server.",
                                            "emoji": {"name": "💰"},
                                            "default": (selected_value == "economy_balance")
                                        },
                                        {
                                            "label": "Fishing: Networth",
                                            "value": "fish_networth",
                                            "description": "Kolektor ikan paling sultan.",
                                            "emoji": {"name": "🐟"},
                                            "default": (selected_value == "fish_networth")
                                        },
                                        {
                                            "label": "Fishing: Heaviest",
                                            "value": "fish_weight",
                                            "description": "Rekor ikan terberat.",
                                            "emoji": {"name": "⚖️"},
                                            "default": (selected_value == "fish_weight")
                                        },
                                        {
                                            "label": "Fishing: Top Fisher",
                                            "value": "fish_catch",
                                            "description": "Paling sering mancing.",
                                            "emoji": {"name": "🎣"},
                                            "default": (selected_value == "fish_catch")
                                        }
                                    ],
                                    "placeholder": "Pilih Kategori...",
                                }
                            ]
                        },
                        {
                            "type": 14, # Spacer
                            "spacing": 1
                        },
                        {
                            "type": 10, # Text Display (Content)
                            "content": content_text
                        }
                    ]
                }
            ]
        }

    def cog_unload(self):
        self.check_loans.cancel()
        # self.conn.close() - Managed by pool now

async def setup(bot):
    await bot.add_cog(Economy(bot))