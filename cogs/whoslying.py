import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import sqlite3
import os

# =============================================
# CONFIGURATION - EDIT THESE TO CUSTOMIZE GAME
# =============================================

THEME_WORD_PAIRS = [
    ("Medsos", ["Instagram", "Twitter", "Facebook", "Youtube", "Tiktok", "Pinterest", "Snapchat", "Discord"]),
    ("Olahraga", ["Sepak Bola", "Basket", "Tenis", "Renang", "Badminton", "Voli", "Golf", "Baseball"]),
    ("Presiden RI", ["Dokter", "Guru", "Gusdur", "Habibi", "Soeharto", "Soekarno", "Megawati", "Susilo Bambang Yudhoyono", "Jokowi"]),
    ("Profesi", ["Dokter", "Guru", "Polisi", "Chef", "Pilot", "Programmer", "Artist", "Lawyer", "Dosen"]),
    ("Transportasi", ["Mobil", "Motor", "Pesawat", "Kapal", "Kereta", "Bus", "Sepeda", "Helikopter", "Getek", "Becak"]),
    ("Buah", ["Apel", "Jeruk", "Pisang", "Mangga", "Strawberry", "Anggur", "Semangka", "Durian", "Rambutan", "Pepaya"]),
    ("Makanan", ["Nasi Goreng", "Pizza", "Burger", "Sushi", "Pasta", "Rendang", "Bakso", "Sate", "Fried Rice", "Indomie"]),
    ("Negara Asia", ["Indonesia", "Malaysia", "Singapura", "Thailand", "Vietnam", "Filipina", "Myanmar", "Kamboja", "Laos", "Brunei","Timor Leste", "China", "Jepang", "Korea Selatan", "Korea Utara","India", "Pakistan", "Nepal", "Afghanistan", "Iran", "Irak",
                    "Arab Saudi", "Uni Emirat Arab", "Qatar", "Yaman", "Palestina","Turki", "Rusia", "Taiwan", "Hong Kong",
    ]),
]

MAX_PLAYERS = 8
MIN_PLAYERS = 2
MAX_SESSIONS = 5
DISCUSSION_TIME = 30  # seconds
VOTE_TIME = 30  # seconds
CLUE_TIMEOUT = 45  # seconds for each player to give clue (increased slightly for modal)

# Initialize database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS game_channels
                 (channel_id INTEGER PRIMARY KEY, guild_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lobby_messages
                 (channel_id INTEGER PRIMARY KEY, message_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS game_players
                 (channel_id INTEGER, user_id INTEGER, 
                  PRIMARY KEY (channel_id, user_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS active_games
                 (channel_id INTEGER PRIMARY KEY,
                  theme TEXT, word TEXT, session INTEGER,
                  impostor_id INTEGER, phase TEXT)''')
    conn.commit()
    conn.close()

init_db()

# =============================================
# GAME IMPLEMENTATION
# =============================================

class WhosLyingGame:
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.players: List[discord.Member] = []
        self.impostor: Optional[discord.Member] = None
        self.current_theme = ""
        self.current_word = ""
        self.current_session = 1
        self.max_sessions = MAX_SESSIONS
        self.game_active = False
        self.clues_given = {}
        self.votes_to_continue = {}
        self.impostor_votes = {}
        self.session_phase = "waiting"
        self.discussion_task = None
        self.control_panel_message = None
        self.voted_players = set()
        self.player_order: List[discord.Member] = []
        self.current_player_index = 0
        self.clue_timeout_task = None
        self.current_clue_giver: Optional[discord.Member] = None
        
    def add_player(self, member: discord.Member) -> bool:
        if len(self.players) >= MAX_PLAYERS:
            return False
        if member not in self.players:
            self.players.append(member)
            self.save_players()
            return True
        return False
    
    def remove_player(self, member: discord.Member) -> bool:
        if member in self.players:
            self.players.remove(member)
            self.save_players()
            return True
        return False
    
    def save_players(self):
        """Save current players to database"""
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("DELETE FROM game_players WHERE channel_id = ?", (self.channel_id,))
        for player in self.players:
            c.execute("INSERT INTO game_players VALUES (?, ?)", (self.channel_id, player.id))
        conn.commit()
        conn.close()
    
    def load_players(self, bot):
        """Load players from database"""
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM game_players WHERE channel_id = ?", (self.channel_id,))
        player_ids = [row[0] for row in c.fetchall()]
        conn.close()
        
        self.players = []
        for user_id in player_ids:
            user = bot.get_user(user_id)
            if user:
                self.players.append(user)
    
    def save_game_state(self):
        """Save current game state to database"""
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        if self.game_active:
            c.execute('''INSERT OR REPLACE INTO active_games 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                     (self.channel_id, self.current_theme, self.current_word,
                      self.current_session, self.impostor.id if self.impostor else None,
                      self.session_phase))
        else:
            c.execute("DELETE FROM active_games WHERE channel_id = ?", (self.channel_id,))
        
        conn.commit()
        conn.close()
    
    def load_game_state(self, bot):
        """Load game state from database"""
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT theme, word, session, impostor_id, phase FROM active_games WHERE channel_id = ?", (self.channel_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            self.current_theme = result[0]
            self.current_word = result[1]
            self.current_session = result[2]
            self.impostor = bot.get_user(result[3]) if result[3] else None
            self.session_phase = result[4]
            self.game_active = True
            
            # Load player order based on current phase
            if self.session_phase == "clue_giving":
                self.player_order = random.sample(self.players, len(self.players))
                self.current_player_index = len(self.clues_given)
    
    def start_game(self) -> bool:
        if len(self.players) < MIN_PLAYERS:
            return False
        
        self.impostor = random.choice(self.players)
        selected_theme, words = random.choice(THEME_WORD_PAIRS)
        self.current_theme = selected_theme
        self.current_word = random.choice(words)
        
        # Randomize player order for clue giving
        self.player_order = random.sample(self.players, len(self.players))
        self.current_player_index = 0
        
        self.game_active = True
        self.current_session = 1
        self.session_phase = "clue_giving"
        self.clues_given = {}
        self.voted_players = set()
        
        # Save game state
        self.save_game_state()
        
        return True
    
    async def next_player_turn(self, cog):
        """Move to next player's turn for giving clue"""
        channel = cog.client.get_channel(self.channel_id)
        if not channel:
            return
        
        # Cancel any existing timeout task
        if self.clue_timeout_task:
            self.clue_timeout_task.cancel()
        
        # Check if all players have given clues
        if len(self.clues_given) >= len(self.players):
            await cog.start_discussion_phase(channel, self)
            return
        
        # Get next player who hasn't given a clue yet
        while self.current_player_index < len(self.player_order):
            next_player = self.player_order[self.current_player_index]
            if next_player.id not in self.clues_given:
                break
            self.current_player_index += 1
        else:
            # All players have given clues
            await cog.start_discussion_phase(channel, self)
            return
        
        self.current_clue_giver = next_player
        self.current_player_index += 1
        
        # Notify channel about current clue giver
        embed = discord.Embed(
            title=f"🎭 Giliran Memberikan Clue - Session {self.current_session}/{self.max_sessions}",
            description=f"Sekarang giliran **{next_player.display_name}** untuk memberikan clue!\n\nKlik tombol **📝 Berikan Clue** di bawah!\n⏳ Waktu: {CLUE_TIMEOUT} detik",
            color=discord.Color.blue()
        )
        
        # Add Give Clue Button
        view = GiveClueView(cog, self)
        await channel.send(embed=embed, view=view)
        
        # Send DM reminder to the player
        try:
            if next_player == self.impostor:
                embed = discord.Embed(
                    title="🎭 Giliranmu Memberikan Clue!",
                    description=f"**Tema:** {self.current_theme}\n\n❗ Kamu adalah IMPOSTOR! Berikan clue yang tidak terlalu spesifik!",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="🔍 Giliranmu Memberikan Clue!",
                    description=f"**Tema:** {self.current_theme}\n**Kata:** ||{self.current_word}||\n\nBerikan clue yang berhubungan dengan kata ini!",
                    color=discord.Color.green()
                )
            await next_player.send(embed=embed)
        except discord.Forbidden:
            pass  # User has DMs disabled
        
        # Set timeout for player to give clue
        self.clue_timeout_task = asyncio.create_task(self.clue_timeout(cog))
    
    async def clue_timeout(self, cog):
        """Handle timeout for player not giving clue"""
        await asyncio.sleep(CLUE_TIMEOUT)
        
        channel = cog.client.get_channel(self.channel_id)
        if not channel or not self.game_active or self.session_phase != "clue_giving":
            return
        
        # Check if current player still hasn't given clue
        if self.current_clue_giver and self.current_clue_giver.id not in self.clues_given:
            self.clues_given[self.current_clue_giver.id] = "(Tidak memberikan clue)"
            self.save_game_state()
            
            embed = discord.Embed(
                title="⏰ Waktu Habis!",
                description=f"**{self.current_clue_giver.display_name}** tidak memberikan clue tepat waktu!",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
        
        # Move to next player
        await self.next_player_turn(cog)
    
    def reset_game(self):
        self.impostor = None
        self.current_theme = ""
        self.current_word = ""
        self.current_session = 1
        self.game_active = False
        self.clues_given = {}
        self.votes_to_continue = {}
        self.impostor_votes = {}
        self.session_phase = "waiting"
        self.voted_players = set()
        self.player_order = []
        self.current_player_index = 0
        self.current_clue_giver = None
        if self.discussion_task:
            self.discussion_task.cancel()
        if self.clue_timeout_task:
            self.clue_timeout_task.cancel()
        
        # Clear game state from database
        self.save_game_state()

# ==========================================
# NEW: Clue Modal & View
# ==========================================

class ClueModal(discord.ui.Modal, title="Berikan Clue"):
    clue_input = discord.ui.TextInput(
        label="Clue Kamu",
        placeholder="Tulis clue yang berhubungan dengan kata...",
        max_length=100
    )

    def __init__(self, cog, game):
        super().__init__()
        self.cog = cog
        self.game = game

    async def on_submit(self, interaction: discord.Interaction):
        clue = self.clue_input.value
        
        self.game.clues_given[interaction.user.id] = clue
        self.game.save_game_state()
        
        await interaction.response.send_message(f"✅ Clue berhasil diberikan: \"{clue}\"", ephemeral=True)
        
        # Cancel timeout task if it exists
        if self.game.clue_timeout_task:
            self.game.clue_timeout_task.cancel()
        
        # Move to next player
        await self.game.next_player_turn(self.cog)

class GiveClueView(discord.ui.View):
    def __init__(self, cog, game):
        super().__init__(timeout=CLUE_TIMEOUT)
        self.cog = cog
        self.game = game

    @discord.ui.button(label="📝 Berikan Clue", style=discord.ButtonStyle.primary)
    async def give_clue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.game.current_clue_giver:
            await interaction.response.send_message(
                f"❌ Sekarang bukan giliranmu! Giliran **{self.game.current_clue_giver.display_name}**.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(ClueModal(self.cog, self.game))

    async def on_timeout(self):
        # Disable button on timeout
        for item in self.children:
            item.disabled = True
        # We don't need to edit the message here necessarily as the game loop handles the timeout logic
        # but disabling the button is good UX.
        pass

# ==========================================
# EXISTING VIEWS (Unchanged mostly)
# ==========================================

class GameResultView(discord.ui.View):
    def __init__(self, cog, game: WhosLyingGame):
        super().__init__(timeout=60)
        self.cog = cog
        self.game = game
        self.add_item(GameResultSelect(cog, game))
    
    async def on_timeout(self):
        channel = self.cog.client.get_channel(self.game.channel_id)
        if channel:
            await self.cog.cleanup_channel(channel, self.game)

class GameResultSelect(discord.ui.Select):
    def __init__(self, cog, game: WhosLyingGame):
        self.cog = cog
        self.game = game
        options = [
            discord.SelectOption(
                label="Main Lagi",
                description="Mulai game baru dengan pemain yang sama",
                emoji="🔄",
                value="restart"
            ),
            discord.SelectOption(
                label="Selesai",
                description="Akhiri game dan kembali ke lobby",
                emoji="⏹️",
                value="finish"
            )
        ]
        super().__init__(
            placeholder="Pilih aksi...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user not in self.game.players:
            await interaction.response.send_message("❌ Hanya pemain yang bisa memilih!", ephemeral=True)
            return
        
        choice = self.values[0]
        
        if choice == "restart":
            await interaction.response.defer()
            await self.cog.cleanup_and_restart(interaction.channel, self.game)
        elif choice == "finish":
            await interaction.response.defer()
            await self.cog.cleanup_channel(interaction.channel, self.game)

class ContinueVoteView(discord.ui.View):
    def __init__(self, game: WhosLyingGame, cog):
        super().__init__(timeout=VOTE_TIME)
        self.game = game
        self.cog = cog
    
    @discord.ui.select(
        placeholder="Pilih: Lanjut atau Vote Impostor?",
        options=[
            discord.SelectOption(
                label="Continue ke Session Berikutnya",
                description="Lanjut ke session berikutnya untuk mendapat lebih banyak clue",
                emoji="✅",
                value="continue"
            ),
            discord.SelectOption(
                label="Vote Impostor Sekarang",
                description="Langsung voting untuk menentukan siapa impostor",
                emoji="🎯",
                value="impostor"
            )
        ]
    )
    async def vote_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user not in self.game.players:
            await interaction.response.send_message("❌ Kamu bukan pemain dalam game ini!", ephemeral=True)
            return
        
        if interaction.user.id in self.game.votes_to_continue:
            await interaction.response.send_message("❌ Kamu sudah memberikan vote!", ephemeral=True)
            return
        
        choice = select.values[0]
        self.game.votes_to_continue[interaction.user.id] = choice
        
        if choice == "continue":
            await interaction.response.send_message(f"✅ {interaction.user.display_name} memilih untuk **CONTINUE**")
        else:
            await interaction.response.send_message(f"🎯 {interaction.user.display_name} memilih untuk **VOTE IMPOSTOR**")
        
        await self.cog.check_continue_votes(interaction.followup, self.game)
    
    async def on_timeout(self):
        channel = self.cog.client.get_channel(self.game.channel_id)
        if channel and self.game.session_phase == "voting_continue":
            # Hitung vote yang sudah masuk
            continue_votes = sum(1 for v in self.game.votes_to_continue.values() if v == "continue")
            impostor_votes = len(self.game.votes_to_continue) - continue_votes
            
            if continue_votes > impostor_votes:
                # Lanjut ke sesi berikutnya
                action = "continue"
                description = "Mayoritas memilih untuk CONTINUE, game dilanjutkan ke session berikutnya."
            else:
                # Vote impostor
                action = "impostor"
                description = "Mayoritas memilih untuk VOTE IMPOSTOR, langsung menuju voting impostor."
            
            embed = discord.Embed(
                title="⏰ Waktu Voting Habis!",
                description=f"{description}\n\nHasil vote:\n✅ CONTINUE: {continue_votes}\n🎯 VOTE IMPOSTOR: {impostor_votes}",
                color=discord.Color.yellow()
            )
            await channel.send(embed=embed)
            
            if action == "continue":
                self.game.current_session += 1
                if self.game.current_session > self.game.max_sessions:
                    self.game.current_session = self.game.max_sessions
                
                # Reset untuk sesi baru
                self.game.clues_given = {}
                self.game.votes_to_continue = {}
                self.game.voted_players = set()
                self.game.player_order = random.sample(self.game.players, len(self.game.players))
                self.game.current_player_index = 0
                self.game.session_phase = "clue_giving"
                self.game.save_game_state()
                
                embed = discord.Embed(
                    title="✅ Game Berlanjut!",
                    description=f"**Session {self.game.current_session}/{self.game.max_sessions}**\nPemberian clue dimulai!",
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
                
                # Mulai giliran pemain pertama
                await self.game.next_player_turn(self.cog)
            else:
                # Mulai voting impostor
                self.game.session_phase = "voting_impostor"
                self.game.impostor_votes = {}
                self.game.voted_players = set()
                self.game.save_game_state()
                
                embed = discord.Embed(
                    title="🎯 Waktunya Vote Impostor!",
                    description="Pemain memilih untuk langsung vote impostor! Gunakan dropdown di bawah untuk memilih siapa impostor.",
                    color=discord.Color.red()
                )
                view = ImpostorVoteView(self.game, self.cog)
                await channel.send(embed=embed, view=view)
            
            # Update control panel
            if self.game.control_panel_message:
                try:
                    view = PersistentGameControlView(self.game, self.cog)
                    embed = self.cog.create_game_embed(self.game)
                    await self.game.control_panel_message.edit(embed=embed, view=view)
                except:
                    pass

class PersistentGameControlView(discord.ui.View):
    def __init__(self, game: WhosLyingGame, cog):
        super().__init__(timeout=None)
        self.game = game
        self.cog = cog
    
    @discord.ui.select(
        placeholder="Pilih aksi...",
        custom_id="game_control_select",
        options=[
            discord.SelectOption(
                label="Join Game",
                description="Bergabung ke dalam game",
                emoji="👥",
                value="join"
            ),
            discord.SelectOption(
                label="Leave Game", 
                description="Keluar dari game",
                emoji="👋",
                value="leave"
            ),
            discord.SelectOption(
                label="Start Game",
                description="Mulai permainan",
                emoji="🎮", 
                value="start"
            ),
            discord.SelectOption(
                label="Stop Game",
                description="Hentikan permainan yang sedang berlangsung",
                emoji="⏹️",
                value="stop"
            )
        ]
    )
    async def game_control_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        choice = select.values[0]
        
        if choice == "join":
            await self.join_game(interaction)
        elif choice == "leave":
            await self.leave_game(interaction)
        elif choice == "start":
            await self.start_game(interaction)
        elif choice == "stop":
            await self.stop_game(interaction)
    
    async def join_game(self, interaction: discord.Interaction):
        if len(self.game.players) >= MAX_PLAYERS:
            await interaction.response.send_message("❌ Game sudah penuh!", ephemeral=True)
            return
            
        if self.game.game_active:
            await interaction.response.send_message("❌ Game sudah dimulai! Tunggu hingga selesai.", ephemeral=True)
            return
        
        if self.game.add_player(interaction.user):
            embed = self.cog.create_lobby_embed(self.game)
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(f"✅ {interaction.user.display_name} bergabung ke game!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Kamu sudah bergabung!", ephemeral=True)
    
    async def leave_game(self, interaction: discord.Interaction):
        if self.game.game_active:
            await interaction.response.send_message("❌ Tidak bisa keluar saat game sedang berlangsung!", ephemeral=True)
            return
            
        if self.game.remove_player(interaction.user):
            embed = self.cog.create_lobby_embed(self.game)
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(f"👋 {interaction.user.display_name} keluar dari game!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Kamu belum bergabung ke game ini!", ephemeral=True)
    
    async def start_game(self, interaction: discord.Interaction):
        if self.game.game_active:
            await interaction.response.send_message("❌ Game sudah berlangsung!", ephemeral=True)
            return
            
        if len(self.game.players) < MIN_PLAYERS:
            await interaction.response.send_message(f"❌ Minimal {MIN_PLAYERS} pemain diperlukan untuk memulai game!", ephemeral=True)
            return
        
        if not self.game.start_game():
            await interaction.response.send_message("❌ Gagal memulai game!", ephemeral=True)
            return
        
        await self.cog.start_game_sequence(self.game)
        embed = self.cog.create_game_embed(self.game)
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send("🎮 Game dimulai! Periksa DM kalian untuk info role!", ephemeral=True)
    
    async def stop_game(self, interaction: discord.Interaction):
        if not self.game.game_active:
            await interaction.response.send_message("❌ Tidak ada game yang sedang berlangsung!", ephemeral=True)
            return
        
        self.game.reset_game()
        embed = self.cog.create_lobby_embed(self.game)
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send("⏹️ Game dihentikan!", ephemeral=True)

class ImpostorVoteView(discord.ui.View):
    def __init__(self, game: WhosLyingGame, cog):
        super().__init__(timeout=30)  # 30 second timeout
        self.game = game
        self.cog = cog
        self.create_buttons()
        self.timeout_task = asyncio.create_task(self.vote_timeout())
    
    async def vote_timeout(self):
        await asyncio.sleep(30)
        if self.game.session_phase == "voting_impostor":
            await self.on_timeout()
    
    def create_buttons(self):
        self.clear_items()
        
        for player in self.game.players:
            button = discord.ui.Button(
                label=f"Vote {player.display_name}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"vote_impostor_{player.id}",
                emoji="🎯"
            )
            button.callback = self.create_vote_callback(player.id, player.display_name)
            self.add_item(button)

    def create_vote_callback(self, target_id: int, target_name: str):
        async def vote_callback(interaction: discord.Interaction):
            if interaction.user not in self.game.players:
                await interaction.response.send_message("❌ Kamu bukan pemain dalam game ini!", ephemeral=True)
                return
            
            if interaction.user.id in self.game.voted_players:
                await interaction.response.send_message("❌ Kamu sudah memberikan vote!", ephemeral=True)
                return
            
            if interaction.user.id == target_id:
                await interaction.response.send_message("❌ Kamu tidak bisa memilih diri sendiri!", ephemeral=True)
                return
            
            self.game.impostor_votes[interaction.user.id] = target_id
            self.game.voted_players.add(interaction.user.id)
            
            await interaction.response.send_message(f"🗳️ {interaction.user.display_name} memilih **{target_name}**")
            
            # Update Embed to show progress
            vote_counts = {}
            for voted_player_id in self.game.impostor_votes.values():
                vote_counts[voted_player_id] = vote_counts.get(voted_player_id, 0) + 1
            
            embed = discord.Embed(
                title="🎯 Voting Impostor!",
                description=f"**{len(self.game.voted_players)}/{len(self.game.players)}** pemain sudah vote\n\n⚠️ **Peraturan:**\n• Setiap pemain hanya bisa vote **1 kali**\n• Tidak bisa memilih diri sendiri",
                color=discord.Color.red()
            )
            
            if vote_counts:
                vote_results = []
                for player_id, votes in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True):
                    player = discord.utils.get(self.game.players, id=player_id)
                    if player:
                        vote_results.append(f"**{player.display_name}:** {votes} vote(s)")
                embed.add_field(name="📊 Hasil Sementara", value="\n".join(vote_results), inline=False)
            
            not_voted = []
            for player in self.game.players:
                if player.id not in self.game.voted_players:
                    not_voted.append(player.display_name)
            
            if not_voted:
                embed.add_field(name="⏳ Belum Vote", value=", ".join(not_voted), inline=False)
            
            try:
                await interaction.message.edit(embed=embed, view=self)
            except:
                pass
            
            if len(self.game.voted_players) == len(self.game.players):
                await self.cog.end_game(interaction.followup, self.game)
        
        return vote_callback
    
    async def on_timeout(self):
        channel = self.cog.client.get_channel(self.game.channel_id)
        if channel and self.game.session_phase == "voting_impostor":
            # Calculate vote counts
            vote_counts = {}
            for voted_player_id in self.game.impostor_votes.values():
                vote_counts[voted_player_id] = vote_counts.get(voted_player_id, 0) + 1
            
            # Determine who was voted as impostor
            if vote_counts:
                voted_impostor_id = max(vote_counts.items(), key=lambda x: x[1])[0]
                voted_impostor = discord.utils.get(self.game.players, id=voted_impostor_id)
            else:
                voted_impostor = None
            
            # Send timeout message
            embed = discord.Embed(
                title="⏰ Waktu Voting Habis!",
                description="Voting berakhir! Hasil akan ditentukan berdasarkan vote yang masuk.",
                color=discord.Color.yellow()
            )
            await channel.send(embed=embed)
            
            # End the game with current votes
            await self.cog.end_game(channel, self.game)

class WhosLying(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.games: Dict[int, WhosLyingGame] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Who\'s Lying Cog is ready')
        # Add persistent view
        self.client.add_view(PersistentGameControlView(None, self))
        # Restore existing lobbies
        await self.restore_lobbies()

    async def restore_lobbies(self):
        """Restore existing lobbies after bot restart"""
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT channel_id, message_id FROM lobby_messages")
        lobbies = c.fetchall()
        conn.close()
        
        for channel_id, message_id in lobbies:
            try:
                channel = self.client.get_channel(channel_id)
                if not channel:
                    continue
                    
                message = await channel.fetch_message(message_id)
                if not message:
                    continue
                
                # Recreate game and load players
                game = self.get_or_create_game(channel_id)
                game.load_players(self.client)
                game.load_game_state(self.client)
                
                # Update message with new view
                if game.game_active:
                    embed = self.create_game_embed(game)
                else:
                    embed = self.create_lobby_embed(game)
                
                view = PersistentGameControlView(game, self)
                await message.edit(embed=embed, view=view)
                game.control_panel_message = message
                
                print(f"✅ Restored lobby in channel {channel_id}")
            except Exception as e:
                print(f"❌ Failed to restore lobby {channel_id}: {e}")
                # Remove invalid lobby from database
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute("DELETE FROM lobby_messages WHERE channel_id = ?", (channel_id,))
                c.execute("DELETE FROM active_games WHERE channel_id = ?", (channel_id,))
                conn.commit()
                conn.close()

    def get_or_create_game(self, channel_id: int) -> WhosLyingGame:
        if channel_id not in self.games:
            self.games[channel_id] = WhosLyingGame(channel_id)
        return self.games[channel_id]

    def create_lobby_embed(self, game: WhosLyingGame) -> discord.Embed:
        embed = discord.Embed(
            title="🎭 Who's Lying? - Game Lobby",
            description="Selamat datang di game Who's Lying! Gunakan selection menu di bawah untuk berinteraksi.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="📊 Players", value=f"{len(game.players)}/{MAX_PLAYERS}", inline=True)
        embed.add_field(name="📝 Status", value="Waiting for players" if not game.game_active else "Game Active", inline=True)
        embed.add_field(name="ℹ️ Info", value=f"Minimum {MIN_PLAYERS} players needed to start", inline=False)
        
        if len(game.players) > 0:
            player_list = "\n".join([f"• {player.display_name}" for player in game.players])
            embed.add_field(name="👥 Player List", value=player_list, inline=False)
        
        embed.add_field(
            name="🎮 Cara Bermain",
            value="• **Join Game:** Bergabung ke lobby\n• **Leave Game:** Keluar dari lobby\n• **Start Game:** Mulai permainan (min 3 pemain)\n• **Stop Game:** Hentikan permainan yang sedang berlangsung",
            inline=False
        )
        return embed
    
    def create_game_embed(self, game: WhosLyingGame) -> discord.Embed:
        phase_text = {
            "clue_giving": "🎨 Pemberian Clue",
            "discussion": "💬 Diskusi",
            "voting_continue": "🗳️ Voting Continue/Impostor",
            "voting_impostor": "🎯 Voting Impostor"
        }
        
        embed = discord.Embed(
            title="🎮 Who's Lying? - Game Active",
            description=f"**Tema:** {game.current_theme}\n**Session:** {game.current_session}/{game.max_sessions}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="📊 Players", value=f"{len(game.players)} pemain", inline=True)
        embed.add_field(name="🎯 Phase", value=phase_text.get(game.session_phase, game.session_phase), inline=True)
        
        if game.session_phase == "clue_giving":
            embed.add_field(name="📝 Clues", value=f"{len(game.clues_given)}/{len(game.players)} given", inline=True)
            embed.add_field(name="💡 Instruksi", value="Pemain memberikan clue bergiliran", inline=False)
        elif game.session_phase == "voting_impostor":
            embed.add_field(name="🗳️ Votes", value=f"{len(game.voted_players)}/{len(game.players)} voted", inline=True)
            embed.add_field(name="💡 Instruksi", value="Gunakan dropdown untuk memilih impostor! (1 vote per pemain)", inline=False)
        
        return embed

    @app_commands.command(name="wl_setup", description="Membuat channel khusus untuk game Who's Lying")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_channel(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Games")
        
        if not category:
            category = await guild.create_category("Games")
        
        channel = await guild.create_text_channel(
            "whos-lying-game",
            category=category,
            topic="Who's Lying Game Room - Use the control panel to play!",
            reason=f"Game channel created by {interaction.user}"
        )
        
        # Save channel to database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO game_channels VALUES (?, ?)", (channel.id, guild.id))
        conn.commit()
        conn.close()
        
        game = self.get_or_create_game(channel.id)
        embed = self.create_lobby_embed(game)
        view = PersistentGameControlView(game, self)
        
        control_message = await channel.send(embed=embed, view=view)
        game.control_panel_message = control_message
        
        # Save lobby message to database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO lobby_messages VALUES (?, ?)", (channel.id, control_message.id))
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(f"✅ Game channel berhasil dibuat: {channel.mention}\n\n🔄 **Lobby akan tetap berfungsi meski bot di-restart!**", ephemeral=True)

    async def send_player_roles(self, game: WhosLyingGame):
        for player in game.players:
            try:
                if player == game.impostor:
                    embed = discord.Embed(
                        title="🎭 Kamu adalah IMPOSTOR!",
                        description=f"**Tema:** {game.current_theme}\n\n❗ Kamu tidak tahu kata spesifiknya! Coba tebak dari clue pemain lain dan berikan clue yang tidak terlalu spesifik.",
                        color=discord.Color.red()
                    )
                else:
                    embed = discord.Embed(
                        title="🔍 Kamu adalah PEMBERI CLUE!",
                        description=f"**Tema:** {game.current_theme}\n**Kata:** ||{game.current_word}||\n\n❗ Berikan clue yang berhubungan dengan kata ini!",
                        color=discord.Color.green()
                    )
                
                await player.send(embed=embed)
            except discord.Forbidden:
                pass  # User has DMs disabled

    async def start_game_sequence(self, game: WhosLyingGame):
        """Start the game sequence after game is started"""
        channel = self.client.get_channel(game.channel_id)
        if not channel:
            return
        
        # Send role information to players
        await self.send_player_roles(game)
        
        # Start first clue giving phase
        game.session_phase = "clue_giving"
        game.save_game_state()
        
        embed = discord.Embed(
            title=f"🎭 Who's Lying? - Session {game.current_session}/{game.max_sessions}",
            description=f"**Tema:** {game.current_theme}\n\nPemain akan memberikan clue bergiliran. Periksa DM kalian untuk instruksi!",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed)
        
        # Start first player's turn
        await game.next_player_turn(self)

    async def start_discussion_phase(self, channel: discord.TextChannel, game: WhosLyingGame):
        """Start the discussion phase after all clues are given"""
        game.session_phase = "discussion"
        game.save_game_state()
        
        # Create a string of all clues
        clues_list = []
        for player in game.players:
            clue = game.clues_given.get(player.id, "(Tidak memberikan clue)")
            clues_list.append(f"• **{player.display_name}:** {clue}")
        
        embed = discord.Embed(
            title=f"💬 Diskusi - Session {game.current_session}/{game.max_sessions}",
            description=f"**Tema:** {game.current_theme}\n\nSemua clue telah diberikan! Diskusikan dengan pemain lain untuk menentukan siapa impostor!",
            color=discord.Color.blue()
        )
        embed.add_field(name="📝 Clues", value="\n".join(clues_list), inline=False)
        embed.set_footer(text=f"Diskusi berlangsung selama {DISCUSSION_TIME} detik")
        
        await channel.send(embed=embed)
        
        # Start discussion timer
        game.discussion_task = asyncio.create_task(self.discussion_timer(channel, game))
    
    async def discussion_timer(self, channel: discord.TextChannel, game: WhosLyingGame):
        """Timer for discussion phase"""
        await asyncio.sleep(DISCUSSION_TIME)
        
        if game.session_phase == "discussion":
            game.session_phase = "voting_continue"
            game.save_game_state()
            
            embed = discord.Embed(
                title="🗳️ Waktunya Voting!",
                description=f"Diskusi selesai! Sekarang vote apakah ingin melanjutkan ke session berikutnya atau langsung vote impostor!",
                color=discord.Color.blue()
            )
            view = ContinueVoteView(game, self)
            await channel.send(embed=embed, view=view)
            
            if game.control_panel_message:
                try:
                    view = PersistentGameControlView(game, self)
                    embed = self.create_game_embed(game)
                    await game.control_panel_message.edit(embed=embed, view=view)
                except:
                    pass

    async def check_continue_votes(self, followup, game: WhosLyingGame):
        """Check if all players have voted to continue or vote impostor"""
        if len(game.votes_to_continue) == len(game.players):
            channel = self.client.get_channel(game.channel_id)
            if not channel:
                return
            
            continue_votes = sum(1 for v in game.votes_to_continue.values() if v == "continue")
            impostor_votes = len(game.players) - continue_votes
            
            if continue_votes > impostor_votes:
                # Continue to next session
                game.current_session += 1
                if game.current_session > game.max_sessions:
                    game.current_session = game.max_sessions
                
                # Reset game state for new session
                game.clues_given = {}
                game.votes_to_continue = {}  # Clear previous votes
                game.voted_players = set()   # Clear voted players
                game.player_order = random.sample(game.players, len(game.players))  # New random order
                game.current_player_index = 0
                game.session_phase = "clue_giving"
                game.save_game_state()
                
                embed = discord.Embed(
                    title="✅ Game Berlanjut!",
                    description=f"**Session {game.current_session}/{game.max_sessions}**\nPemberian clue dimulai!",
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
                
                # Update control panel
                if game.control_panel_message:
                    try:
                        view = PersistentGameControlView(game, self)
                        embed = self.create_game_embed(game)
                        await game.control_panel_message.edit(embed=embed, view=view)
                    except:
                        pass
                
                # Start first player's turn in new session
                await game.next_player_turn(self)
            else:
                # Start impostor voting
                game.session_phase = "voting_impostor"
                game.impostor_votes = {}  # Clear previous votes
                game.voted_players = set()  # Clear voted players
                game.save_game_state()
                
                embed = discord.Embed(
                    title="🎯 Waktunya Vote Impostor!",
                    description="Pemain memilih untuk langsung vote impostor! Gunakan dropdown di bawah untuk memilih siapa impostor.",
                    color=discord.Color.red()
                )
                view = ImpostorVoteView(game, self)
                await channel.send(embed=embed, view=view)
                
                if game.control_panel_message:
                    try:
                        view = PersistentGameControlView(game, self)
                        embed = self.create_game_embed(game)
                        await game.control_panel_message.edit(embed=embed, view=view)
                    except:
                        pass

    async def end_game(self, channel_or_followup, game: WhosLyingGame):
        """End the game and show results"""
        if isinstance(channel_or_followup, discord.Webhook):
            channel = self.client.get_channel(game.channel_id)
            followup = channel_or_followup
        else:
            channel = channel_or_followup
            followup = channel
        
        if not channel:
            return
        
        # Calculate votes
        vote_counts = {}
        for voted_player_id in game.impostor_votes.values():
            vote_counts[voted_player_id] = vote_counts.get(voted_player_id, 0) + 1
        
        # Determine who was voted as impostor
        if vote_counts:
            voted_impostor_id = max(vote_counts.items(), key=lambda x: x[1])[0]
            voted_impostor = discord.utils.get(game.players, id=voted_impostor_id)
        else:
            voted_impostor = None
        
        # Create results embed
        embed = discord.Embed(
            title="🎭 Game Selesai!",
            description="Berikut adalah hasil dari game Who's Lying!",
            color=discord.Color.gold()
        )
        
        # Add impostor information
        if game.impostor:
            embed.add_field(
                name="🎭 Impostor Sebenarnya",
                value=f"{game.impostor.display_name}",
                inline=False
            )
        
        # Add voting results
        if voted_impostor:
            embed.add_field(
                name="🎯 Impostor yang Dipilih",
                value=f"{voted_impostor.display_name} (dengan {vote_counts[voted_impostor.id]} vote)",
                inline=False
            )
            
            # Determine if players guessed correctly
            if voted_impostor == game.impostor:
                embed.add_field(
                    name="🏆 Hasil",
                    value="Pemain berhasil menebak impostor!",
                    inline=False
                )
                embed.color = discord.Color.green()
            else:
                embed.add_field(
                    name="💀 Hasil",
                    value="Pemain gagal menebak impostor!",
                    inline=False
                )
                embed.color = discord.Color.red()
        else:
            embed.add_field(
                name="❌ Tidak Ada Vote",
                value="Tidak ada yang memberikan vote!",
                inline=False
            )
        
        # Add the actual word
        embed.add_field(
            name="🔍 Kata Sebenarnya",
            value=game.current_word,
            inline=False
        )
        
        # Show all clues
        clues_list = []
        for player in game.players:
            clue = game.clues_given.get(player.id, "(Tidak memberikan clue)")
            if player == game.impostor:
                clues_list.append(f"• 🎭 **{player.display_name}:** {clue} (IMPOSTOR)")
            else:
                clues_list.append(f"• **{player.display_name}:** {clue}")
        
        embed.add_field(
            name="📝 Semua Clue",
            value="\n".join(clues_list),
            inline=False
        )
        
        view = GameResultView(self, game)
        await channel.send(embed=embed, view=view)
        
        # Reset game state
        game.reset_game()
        
        # Update control panel
        if game.control_panel_message:
            try:
                embed = self.create_lobby_embed(game)
                view = PersistentGameControlView(game, self)
                await game.control_panel_message.edit(embed=embed, view=view)
            except:
                pass

    async def cleanup_channel(self, channel: discord.TextChannel, game: WhosLyingGame):
        """Cleanup the game channel"""
        game.reset_game()
        
        # OPTIMIZED CLEANUP: Purge messages instead of iterating history
        # Keep the control panel message if possible
        
        def is_not_control_panel(m):
            return m.id != game.control_panel_message.id if game.control_panel_message else True

        try:
            # Delete last 100 messages that aren't the control panel
            await channel.purge(limit=100, check=is_not_control_panel)
        except discord.Forbidden:
            pass  # No permission
        except Exception as e:
            print(f"Error purging channel: {e}")
        
        # Update control panel
        embed = self.create_lobby_embed(game)
        view = PersistentGameControlView(game, self)
        
        if game.control_panel_message:
            try:
                await game.control_panel_message.edit(embed=embed, view=view)
            except:
                game.control_panel_message = await channel.send(embed=embed, view=view)
        else:
            game.control_panel_message = await channel.send(embed=embed, view=view)
        
        # Save lobby message to database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO lobby_messages VALUES (?, ?)", (channel.id, game.control_panel_message.id))
        conn.commit()
        conn.close()

    async def cleanup_and_restart(self, channel: discord.TextChannel, game: WhosLyingGame):
        """Cleanup and restart the game"""
        game.reset_game()
        
        # OPTIMIZED CLEANUP
        def is_not_control_panel(m):
            return m.id != game.control_panel_message.id if game.control_panel_message else True

        try:
            await channel.purge(limit=100, check=is_not_control_panel)
        except discord.Forbidden:
            pass
        
        # Update control panel
        embed = self.create_lobby_embed(game)
        view = PersistentGameControlView(game, self)
        
        if game.control_panel_message:
            try:
                await game.control_panel_message.edit(embed=embed, view=view)
            except:
                game.control_panel_message = await channel.send(embed=embed, view=view)
        else:
            game.control_panel_message = await channel.send(embed=embed, view=view)
        
        # Save lobby message to database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO lobby_messages VALUES (?, ?)", (channel.id, game.control_panel_message.id))
        conn.commit()
        conn.close()
        
        # Start new game
        if len(game.players) >= MIN_PLAYERS:
            if game.start_game():
                await self.start_game_sequence(game)

async def setup(client):
    await client.add_cog(WhosLying(client))
