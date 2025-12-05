import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import random
import sqlite3
from typing import Dict, Optional, List

class RPSGame:
    """Class to manage individual RPS game sessions"""
    def __init__(self, player1: discord.Member, player2: discord.Member, bet: int = 0):
        self.player1 = player1
        self.player2 = player2
        self.bet = bet
        self.choices: Dict[int, Optional[str]] = {player1.id: None, player2.id: None}
        self.session_wins: Dict[int, int] = {player1.id: 0, player2.id: 0}  # Wins in current session
        self.is_active = True
        self.rounds_played = 0
        self.win_target = 3  # First to 3 wins

    def make_choice(self, player_id: int, choice: str) -> bool:
        """Make a choice for a player. Returns True if both players have chosen."""
        if player_id in self.choices and self.choices[player_id] is None:
            self.choices[player_id] = choice
            return all(choice is not None for choice in self.choices.values())
        return False

    def get_round_winner(self) -> Optional[discord.Member]:
        """Determine the winner of the current round"""
        if None in self.choices.values():
            return None
        
        choice1 = self.choices[self.player1.id]
        choice2 = self.choices[self.player2.id]
        
        if choice1 == choice2:
            return None  # Tie
        
        win_conditions = {
            "Batu": "Gunting",
            "Gunting": "Kertas", 
            "Kertas": "Batu"
        }
        
        return self.player1 if win_conditions[choice1] == choice2 else self.player2

    def add_round_win(self, winner: discord.Member) -> bool:
        """Add a win to the session. Returns True if game is complete (someone reached win_target)"""
        if winner:
            self.session_wins[winner.id] += 1
            return self.session_wins[winner.id] >= self.win_target
        return False

    def get_session_winner(self) -> Optional[discord.Member]:
        """Get the overall session winner (first to reach win_target)"""
        for player_id, wins in self.session_wins.items():
            if wins >= self.win_target:
                return self.player1 if player_id == self.player1.id else self.player2
        return None

    def reset_choices(self):
        """Reset choices for a new round"""
        self.choices = {self.player1.id: None, self.player2.id: None}
        self.rounds_played += 1

    def get_score_display(self) -> str:
        """Get formatted score display"""
        return f"{self.session_wins[self.player1.id]}-{self.session_wins[self.player2.id]}"

class RPSView(View):
    """View for RPS game buttons"""
    def __init__(self, game: RPSGame, cog):
        super().__init__(timeout=300)  # 5 minute timeout
        self.game = game
        self.cog = cog
        self.emojis = {"Batu": "✊", "Gunting": "✌️", "Kertas": "📰"}
        
        # Create buttons for each choice
        for choice in ["Batu", "Gunting", "Kertas"]:
            self.add_item(RPSButton(choice, self.emojis[choice], self.game, self.cog))

    async def on_timeout(self):
        """Handle view timeout"""
        if self.game.is_active:
            self.game.is_active = False
            # Optionally notify players about timeout
            if hasattr(self.game, 'channel'):
                timeout_embed = discord.Embed(
                    title="⏰ Permainan Timeout",
                    description="Permainan berakhir karena tidak ada aktivitas.",
                    color=discord.Color.red()
                )
                await self.game.channel.send(embed=timeout_embed)

class RPSButton(Button):
    """Button for RPS choices"""
    def __init__(self, choice: str, emoji: str, game: RPSGame, cog):
        super().__init__(label=choice, style=discord.ButtonStyle.primary, emoji=emoji)
        self.choice = choice
        self.game = game
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not self.game.is_active:
            await interaction.response.send_message("❌ Permainan ini sudah berakhir!", ephemeral=True)
            return

        if interaction.user.id not in self.game.choices:
            await interaction.response.send_message("❌ Anda bukan pemain dalam permainan ini!", ephemeral=True)
            return

        if self.game.choices[interaction.user.id] is not None:
            await interaction.response.send_message("❌ Anda sudah memilih untuk ronde ini!", ephemeral=True)
            return

        # Make the choice
        both_chosen = self.game.make_choice(interaction.user.id, self.choice)
        
        await interaction.response.send_message(
            f"✅ Anda memilih: {self.view.emojis[self.choice]} **{self.choice}**\n"
            f"{'🎯 Menunggu pemain lain...' if not both_chosen else '🎮 Kedua pemain telah memilih!'}",
            ephemeral=True
        )

        if both_chosen:
            await self.cog.show_round_result(self.game, self.game.channel)

class PostGameView(View):
    """View for post-game actions"""
    def __init__(self, game: RPSGame, cog):
        super().__init__(timeout=300)  # 5 minute timeout
        self.game = game
        self.cog = cog

    @discord.ui.button(label="🔄 Main Lagi", style=discord.ButtonStyle.success)
    async def play_again(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in [self.game.player1.id, self.game.player2.id]:
            await interaction.response.send_message("❌ Hanya pemain yang bisa memulai permainan baru!", ephemeral=True)
            return

        # Check balance again for both players if there was a bet
        if self.game.bet > 0:
            economy = self.cog.get_economy()
            if economy:
                p1_bal = economy.get_balance(self.game.player1.id)
                p2_bal = economy.get_balance(self.game.player2.id)
                
                if p1_bal < self.game.bet or p2_bal < self.game.bet:
                    await interaction.response.send_message("❌ Salah satu pemain tidak memiliki cukup saldo untuk main lagi!", ephemeral=True)
                    return

        await interaction.response.send_message("🎮 Memulai permainan baru...", ephemeral=True)
        await self.cog.start_new_game(self.game.player1, self.game.player2, self.game.channel, bet=self.game.bet)

    @discord.ui.button(label="📊 Lihat Statistik", style=discord.ButtonStyle.secondary)
    async def view_stats(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(embed=self.cog.create_session_stats_embed(self.game), ephemeral=True)

    @discord.ui.button(label="🏁 Akhiri", style=discord.ButtonStyle.danger)
    async def end_session(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in [self.game.player1.id, self.game.player2.id]:
            await interaction.response.send_message("❌ Hanya pemain yang bisa mengakhiri sesi!", ephemeral=True)
            return

        self.game.is_active = False
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True

        final_embed = self.cog.create_final_session_embed(self.game)
        await interaction.response.edit_message(embed=final_embed, view=self)

        # Clean up the game
        if self.game.channel.id in self.cog.active_games:
            del self.cog.active_games[self.game.channel.id]

class RPS(commands.Cog):
    """Rock Paper Scissors game cog"""
    
    def __init__(self, client):
        self.client = client
        self.active_games: Dict[int, RPSGame] = {}
        self.conn = sqlite3.connect('database.db')
        self._init_db()
        self.emojis = {"Batu": "✊", "Gunting": "✌️", "Kertas": "📰"}

    def get_economy(self):
        return self.client.get_cog('Economy')

    def _init_db(self):
        """Initialize database tables"""
        cursor = self.conn.cursor()
        
        # Main stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rps_stats (
                user_id INTEGER PRIMARY KEY,
                total_games INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                games_lost INTEGER DEFAULT 0,
                rounds_won INTEGER DEFAULT 0,
                rounds_lost INTEGER DEFAULT 0,
                rounds_tied INTEGER DEFAULT 0,
                last_played INTEGER DEFAULT 0
            )
        ''')
        
        # Session history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rps_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1_id INTEGER,
                player2_id INTEGER,
                winner_id INTEGER,
                player1_score INTEGER,
                player2_score INTEGER,
                rounds_played INTEGER,
                timestamp INTEGER
            )
        ''')
        
        self.conn.commit()

    def cog_unload(self):
        """Close database connection when cog is unloaded"""
        self.conn.close()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'✅ RPS Cog is ready')

    def get_player_stats(self, user_id: int) -> Dict[str, int]:
        """Get player statistics from database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT total_games, games_won, games_lost, rounds_won, rounds_lost, rounds_tied
            FROM rps_stats WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                'total_games': result[0],
                'games_won': result[1],
                'games_lost': result[2],
                'rounds_won': result[3],
                'rounds_lost': result[4],
                'rounds_tied': result[5]
            }
        else:
            # Create new player entry
            cursor.execute('''
                INSERT INTO rps_stats (user_id) VALUES (?)
            ''', (user_id,))
            self.conn.commit()
            return {
                'total_games': 0,
                'games_won': 0,
                'games_lost': 0,
                'rounds_won': 0,
                'rounds_lost': 0,
                'rounds_tied': 0
            }

    def update_game_stats(self, game: RPSGame, session_winner: discord.Member):
        """Update game statistics after a session ends"""
        cursor = self.conn.cursor()
        import time
        
        player1, player2 = game.player1, game.player2
        winner_id = session_winner.id if session_winner else None
        loser_id = player2.id if session_winner == player1 else player1.id if session_winner else None
        
        # Update total games and wins/losses
        if winner_id and loser_id:
            # Winner stats
            cursor.execute('''
                UPDATE rps_stats 
                SET total_games = total_games + 1, 
                    games_won = games_won + 1,
                    rounds_won = rounds_won + ?,
                    rounds_lost = rounds_lost + ?,
                    rounds_tied = rounds_tied + ?,
                    last_played = ?
                WHERE user_id = ?
            ''', (
                game.session_wins[winner_id],
                game.session_wins[loser_id],
                0,  # ties in this implementation are per round, but we're tracking game-level
                int(time.time()),
                winner_id
            ))
            
            # Loser stats
            cursor.execute('''
                UPDATE rps_stats 
                SET total_games = total_games + 1, 
                    games_lost = games_lost + 1,
                    rounds_won = rounds_won + ?,
                    rounds_lost = rounds_lost + ?,
                    rounds_tied = rounds_tied + ?,
                    last_played = ?
                WHERE user_id = ?
            ''', (
                game.session_wins[loser_id],
                game.session_wins[winner_id],
                0,
                int(time.time()),
                loser_id
            ))
        
        # Record session in history
        cursor.execute('''
            INSERT INTO rps_sessions 
            (player1_id, player2_id, winner_id, player1_score, player2_score, rounds_played, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            player1.id,
            player2.id,
            winner_id,
            game.session_wins[player1.id],
            game.session_wins[player2.id],
            game.rounds_played,
            int(time.time())
        ))
        
        self.conn.commit()

    def update_round_stats(self, winner_id: Optional[int], loser_id: Optional[int], is_tie: bool = False):
        """Update round-level statistics"""
        cursor = self.conn.cursor()
        import time
        
        if is_tie and winner_id and loser_id:
            # Both players get a tie
            cursor.execute('''
                UPDATE rps_stats 
                SET rounds_tied = rounds_tied + 1, last_played = ?
                WHERE user_id IN (?, ?)
            ''', (int(time.time()), winner_id, loser_id))
        elif winner_id and loser_id:
            # Winner gets a round win
            cursor.execute('''
                UPDATE rps_stats 
                SET rounds_won = rounds_won + 1, last_played = ?
                WHERE user_id = ?
            ''', (int(time.time()), winner_id))
            
            # Loser gets a round loss
            cursor.execute('''
                UPDATE rps_stats 
                SET rounds_lost = rounds_lost + 1, last_played = ?
                WHERE user_id = ?
            ''', (int(time.time()), loser_id))
        
        self.conn.commit()

    def create_session_stats_embed(self, game: RPSGame) -> discord.Embed:
        """Create current session statistics embed"""
        embed = discord.Embed(
            title="📊 Statistik Sesi Saat Ini",
            color=discord.Color.blue()
        )
        
        p1_score = game.session_wins[game.player1.id]
        p2_score = game.session_wins[game.player2.id]
        
        embed.add_field(
            name="🎯 Skor Sesi",
            value=f"**{game.player1.display_name}**: {p1_score} menang\n"
                  f"**{game.player2.display_name}**: {p2_score} menang\n"
                  f"🎮 Ronde dimainkan: {game.rounds_played}\n"
                  f"🏆 Target kemenangan: {game.win_target}",
            inline=False
        )
        
        if game.bet > 0:
            embed.add_field(name="💰 Taruhan", value=f"{game.bet} koin", inline=False)
        
        if game.rounds_played > 0:
            remaining_wins_p1 = max(0, game.win_target - p1_score)
            remaining_wins_p2 = max(0, game.win_target - p2_score)
            
            embed.add_field(
                name="🎯 Sisa Kemenangan yang Dibutuhkan",
                value=f"**{game.player1.display_name}**: {remaining_wins_p1}\n"
                      f"**{game.player2.display_name}**: {remaining_wins_p2}",
                inline=False
            )
        
        return embed

    def create_final_session_embed(self, game: RPSGame) -> discord.Embed:
        """Create final session statistics embed"""
        session_winner = game.get_session_winner()
        
        embed = discord.Embed(
            title="🏁 Sesi Berakhir!",
            color=discord.Color.gold()
        )
        
        if session_winner:
            embed.description = f"🏆 **{session_winner.display_name}** memenangkan sesi ini!"
            if game.bet > 0:
                embed.description += f"\n\n💰 **Menang {game.bet} koin!**"
        else:
            embed.description = "🤝 Sesi berakhir tanpa pemenang"
        
        embed.add_field(
            name="📊 Hasil Akhir",
            value=f"**{game.player1.display_name}**: {game.session_wins[game.player1.id]} menang\n"
                  f"**{game.player2.display_name}**: {game.session_wins[game.player2.id]} menang\n"
                  f"🎮 Total ronde: {game.rounds_played}",
            inline=False
        )
        
        embed.set_footer(text="Terima kasih telah bermain!")
        return embed

    @app_commands.command(name="rps", description="🎮 Tantang temanmu dalam permainan Batu Gunting Kertas! (First to 3 wins)")
    @app_commands.describe(member="Lawan yang ingin ditantang", bet="Jumlah taruhan (opsional)")
    async def rps(self, interaction: discord.Interaction, member: discord.Member, bet: int = 0):
        """Main RPS command"""
        
        # Validation checks
        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="❌ Error",
                description="Anda tidak dapat menantang diri sendiri!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if member.bot:
            embed = discord.Embed(
                title="❌ Error", 
                description="Anda tidak dapat menantang bot!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Economy check
        if bet > 0:
            economy = self.get_economy()
            if not economy:
                await interaction.response.send_message("❌ Sistem ekonomi belum siap!", ephemeral=True)
                return
                
            p1_bal = economy.get_balance(interaction.user.id)
            p2_bal = economy.get_balance(member.id)
            
            if p1_bal < bet:
                await interaction.response.send_message(f"❌ Anda tidak memiliki cukup saldo! (Butuh: {bet}, Ada: {p1_bal})", ephemeral=True)
                return
                
            if p2_bal < bet:
                await interaction.response.send_message(f"❌ Lawan tidak memiliki cukup saldo! (Butuh: {bet}, Ada: {p2_bal})", ephemeral=True)
                return

        # Check if either player is already in a game
        if any(game.is_active and (interaction.user.id in [game.player1.id, game.player2.id] or 
                                  member.id in [game.player1.id, game.player2.id]) 
               for game in self.active_games.values()):
            embed = discord.Embed(
                title="❌ Error",
                description="Salah satu pemain sedang dalam permainan lain!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.start_new_game(interaction.user, member, interaction.channel, interaction, bet)

    async def start_new_game(self, player1: discord.Member, player2: discord.Member, 
                           channel: discord.TextChannel, interaction: discord.Interaction = None, bet: int = 0):
        """Start a new RPS game session"""
        
        # Clean up any existing game in this channel
        if channel.id in self.active_games:
            del self.active_games[channel.id]
        
        # Create new game
        game = RPSGame(player1, player2, bet)
        game.channel = channel
        self.active_games[channel.id] = game
        
        # Initialize player stats in database
        self.get_player_stats(player1.id)
        self.get_player_stats(player2.id)
        
        # Create game view
        view = RPSView(game, self)
        
        # Create DM embed
        dm_embed = discord.Embed(
            title="🎮 Pilih Gerakan Anda!",
            description=f"**First to 3 Wins!**\n\n"
                       f"Pilih salah satu:\n"
                       f"✊ **Batu** - Mengalahkan Gunting\n"
                       f"✌️ **Gunting** - Mengalahkan Kertas\n"
                       f"📰 **Kertas** - Mengalahkan Batu",
            color=discord.Color.blurple()
        )
        
        # Create public challenge embed
        desc = f"**{player1.display_name}** menantang **{player2.display_name}**!\n\n" \
               f"🏆 **First to 3 Wins!**\n"
        
        if bet > 0:
            desc += f"💰 **Taruhan: {bet} koin**\n"
            
        desc += f"🔐 Pemilihan sedang berlangsung di DM...\n" \
                f"📊 Hasil akan ditampilkan di sini setelah kedua pemain memilih."
               
        public_embed = discord.Embed(
            title="🎮 Tantangan Batu Gunting Kertas!",
            description=desc,
            color=discord.Color.orange()
        )
        public_embed.set_footer(text="Periksa DM Anda untuk memilih gerakan!")
        
        try:
            # Send DM to both players
            await player1.send(f"🎯 **Tantangan RPS!**", embed=dm_embed, view=view)
            await player2.send(f"🎯 **{player1.display_name} menantang Anda!**", embed=dm_embed, view=view)
            
            # Send public challenge announcement
            if interaction:
                await interaction.response.send_message(embed=public_embed)
            else:
                await channel.send(embed=public_embed)
                
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Error",
                description="Gagal mengirim tantangan ke DM!\n"
                           "Pastikan kedua pemain telah mengaktifkan DM dari anggota server.",
                color=discord.Color.red()
            )
            
            if interaction:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await channel.send(embed=error_embed)
            
            # Remove the failed game
            if channel.id in self.active_games:
                del self.active_games[channel.id]

    async def show_round_result(self, game: RPSGame, channel: discord.TextChannel):
        """Show individual round result and check for session end"""
        if not game.is_active:
            return
            
        round_winner = game.get_round_winner()
        player1, player2 = game.player1, game.player2
        choice1 = game.choices[player1.id]
        choice2 = game.choices[player2.id]
        
        # Create round result embed
        result_embed = discord.Embed(
            title=f"🎯 Hasil Ronde {game.rounds_played + 1}",
            color=discord.Color.blue()
        )
        
        result_embed.add_field(
            name="🎮 Pilihan",
            value=f"{self.emojis[choice1]} **{player1.display_name}**: {choice1}\n"
                  f"{self.emojis[choice2]} **{player2.display_name}**: {choice2}",
            inline=False
        )
        
        # Determine round result and update stats
        if round_winner is None:
            result_text = "🤝 **SERI!**"
            result_color = discord.Color.orange()
            # Update round tie stats
            self.update_round_stats(player1.id, player2.id, is_tie=True)
        else:
            result_text = f"🏆 **{round_winner.display_name} MENANG RONDE!**"
            result_color = discord.Color.green()
            loser = player2 if round_winner == player1 else player1
            # Update round win/loss stats
            self.update_round_stats(round_winner.id, loser.id)
        
        # Check if someone won the session
        session_complete = game.add_round_win(round_winner)
        
        result_embed.add_field(name="📊 Hasil Ronde", value=result_text, inline=False)
        result_embed.color = result_color
        
        # Add current session score
        result_embed.add_field(
            name="🏆 Skor Sesi",
            value=f"**{player1.display_name}**: {game.session_wins[player1.id]}\n"
                  f"**{player2.display_name}**: {game.session_wins[player2.id]}\n"
                  f"🎯 Target: {game.win_target} kemenangan",
            inline=False
        )
        
        # Reset choices for next round
        game.reset_choices()
        
        # Send round result
        await channel.send(embed=result_embed)
        
        # Check if session is complete
        if session_complete:
            session_winner = game.get_session_winner()
            game.is_active = False
            
            # Handle economy if there was a bet
            if game.bet > 0 and session_winner:
                economy = self.get_economy()
                if economy:
                    loser = player2 if session_winner == player1 else player1
                    # Double check balances before transfer (just in case)
                    if economy.get_balance(loser.id) >= game.bet:
                        economy.transfer_money(loser.id, session_winner.id, game.bet)
                        # Note: transfer_money handles deduction from sender and addition to receiver
            
            # Update game-level statistics
            self.update_game_stats(game, session_winner)
            
            # Create session end embed
            session_end_embed = discord.Embed(
                title="🎉 SESI BERAKHIR!",
                description=f"🏆 **{session_winner.display_name}** memenangkan sesi dengan {game.win_target} kemenangan!",
                color=discord.Color.gold()
            )
            
            if game.bet > 0:
                session_end_embed.add_field(name="💰 Taruhan", value=f"Pemenang mendapatkan **{game.bet}** koin!", inline=False)
            
            session_end_embed.add_field(
                name="📊 Hasil Akhir",
                value=f"**{player1.display_name}**: {game.session_wins[player1.id]} menang\n"
                      f"**{player2.display_name}**: {game.session_wins[player2.id]} menang\n"
                      f"🎮 Total ronde: {game.rounds_played}",
                inline=False
            )
            
            # Get updated overall stats
            stats1 = self.get_player_stats(player1.id)
            stats2 = self.get_player_stats(player2.id)
            
            session_end_embed.add_field(
                name="📈 Statistik Overall",
                value=f"**{player1.display_name}**: {stats1['games_won']}-{stats1['games_lost']} (games)\n"
                      f"**{player2.display_name}**: {stats2['games_won']}-{stats2['games_lost']} (games)",
                inline=False
            )
            
            await channel.send(embed=session_end_embed)
            
            # Send post-game options
            post_game_view = PostGameView(game, self)
            options_embed = discord.Embed(
                title="🎮 Apa selanjutnya?",
                description="Pilih aksi yang ingin dilakukan:",
                color=discord.Color.blurple()
            )
            
            await channel.send(embed=options_embed, view=post_game_view)
            
        else:
            # Continue to next round - send new DM buttons
            view = RPSView(game, self)
            
            next_round_embed = discord.Embed(
                title=f"🎮 Ronde {game.rounds_played + 1}",
                description=f"Pilih gerakan untuk ronde berikutnya!\n\n"
                           f"**Skor Saat Ini:**\n"
                           f"{player1.display_name}: {game.session_wins[player1.id]}\n"
                           f"{player2.display_name}: {game.session_wins[player2.id]}",
                color=discord.Color.blurple()
            )
            
            try:
                await player1.send(embed=next_round_embed, view=view)
                await player2.send(embed=next_round_embed, view=view)
            except discord.Forbidden:
                # If DM fails, end the game
                await channel.send("❌ Tidak dapat melanjutkan permainan. DM tidak dapat dikirim.")
                game.is_active = False
                del self.active_games[channel.id]

    @app_commands.command(name="rps_stats", description="📊 Lihat statistik permainan RPS Anda atau pemain lain")
    async def rps_stats(self, interaction: discord.Interaction, member: discord.Member = None):
        """View detailed RPS statistics"""
        target = member or interaction.user
        
        if target.bot:
            await interaction.response.send_message("❌ Bot tidak memiliki statistik!", ephemeral=True)
            return
        
        stats = self.get_player_stats(target.id)
        
        embed = discord.Embed(
            title=f"📊 Statistik RPS - {target.display_name}",
            color=discord.Color.blue()
        )
        
        # Game-level stats
        embed.add_field(
            name="🏆 Statistik Permainan",
            value=f"🎮 Total Games: {stats['total_games']}\n"
                  f"✅ Games Won: {stats['games_won']}\n"
                  f"❌ Games Lost: {stats['games_lost']}\n",
            inline=True
        )
        
        # Round-level stats  
        total_rounds = stats['rounds_won'] + stats['rounds_lost'] + stats['rounds_tied']
        embed.add_field(
            name="⚡ Statistik Ronde",
            value=f"🎯 Total Rounds: {total_rounds}\n"
                  f"✅ Rounds Won: {stats['rounds_won']}\n"
                  f"❌ Rounds Lost: {stats['rounds_lost']}\n"
                  f"🤝 Rounds Tied: {stats['rounds_tied']}",
            inline=True
        )
        
        # Calculate rates
        if stats['total_games'] > 0:
            game_win_rate = (stats['games_won'] / stats['total_games']) * 100
            embed.add_field(
                name="📈 Win Rates",
                value=f"Game Win Rate: {game_win_rate:.1f}%",
                inline=False
            )
            
            if total_rounds > 0:
                round_win_rate = (stats['rounds_won'] / total_rounds) * 100
                embed.add_field(
                    name="📈 Round Win Rate",
                    value=f"Round Win Rate: {round_win_rate:.1f}%",
                    inline=True
                )
        
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text="Gunakan /rps untuk bermain! First to 3 wins!")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rps_leaderboard", description="🏆 Lihat papan peringkat RPS server")
    async def rps_leaderboard(self, interaction: discord.Interaction, sort_by: str = "games"):
        """Display RPS leaderboard with different sorting options"""
        
        cursor = self.conn.cursor()
        
        # Define sorting options
        sort_options = {
            "games": ("games_won", "Games Won"),
            "winrate": ("(games_won * 1.0 / CASE WHEN total_games = 0 THEN 1 ELSE total_games END)", "Win Rate"),
            "rounds": ("rounds_won", "Rounds Won"),
            "total": ("total_games", "Total Games")
        }
        
        if sort_by not in sort_options:
            sort_by = "games"
        
        sort_column, sort_name = sort_options[sort_by]
        
        # Get top 10 players
        cursor.execute(f'''
            SELECT user_id, total_games, games_won, games_lost, rounds_won, rounds_lost, rounds_tied
            FROM rps_stats 
            WHERE total_games > 0
            ORDER BY {sort_column} DESC, total_games DESC
            LIMIT 10
        ''')
        top_players = cursor.fetchall()
        
        if not top_players:
            embed = discord.Embed(
                title="🏆 Papan Peringkat RPS",
                description="Belum ada yang bermain RPS di server ini!\nGunakan `/rps @member` untuk memulai.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        embed = discord.Embed(
            title="🏆 Papan Peringkat RPS",
            description=f"Top 10 pemain RPS (diurutkan berdasarkan {sort_name}):",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        leaderboard_text = ""
        
        for i, (user_id, total_games, games_won, games_lost, rounds_won, rounds_lost, rounds_tied) in enumerate(top_players):
            try:
                user = await self.client.fetch_user(user_id)
                medal = medals[i] if i < 3 else f"**{i+1}.**"
                
                # Calculate win rates
                game_win_rate = (games_won / max(1, total_games)) * 100
                total_rounds = rounds_won + rounds_lost + rounds_tied
                round_win_rate = (rounds_won / max(1, total_rounds)) * 100
                
                # Format based on sort type
                if sort_by == "games":
                    main_stat = f"🏆 {games_won} games"
                elif sort_by == "winrate":
                    main_stat = f"📊 {game_win_rate:.1f}% win rate"
                elif sort_by == "rounds":
                    main_stat = f"⚡ {rounds_won} rounds"
                else:  # total
                    main_stat = f"🎮 {total_games} games"
                
                leaderboard_text += f"{medal} **{user.display_name}**\n"
                leaderboard_text += f"└ {main_stat} • {total_games} total games\n\n"
                
            except discord.NotFound:
                continue
        
        embed.description += f"\n\n{leaderboard_text}"
        embed.set_footer(text="💡 Tip: First to 3 wins in each game session!")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rps_history", description="📋 Lihat riwayat permainan RPS Anda")
    async def rps_history(self, interaction: discord.Interaction, member: discord.Member = None):
        """View recent RPS game history"""
        target = member or interaction.user
        
        if target.bot:
            await interaction.response.send_message("❌ Bot tidak memiliki riwayat permainan!", ephemeral=True)
            return
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT player1_id, player2_id, winner_id, player1_score, player2_score, rounds_played, timestamp
            FROM rps_sessions 
            WHERE player1_id = ? OR player2_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (target.id, target.id))
        
        history = cursor.fetchall()
        
        if not history:
            embed = discord.Embed(
                title=f"📋 Riwayat RPS - {target.display_name}",
                description="Belum ada riwayat permainan!",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"📋 Riwayat RPS - {target.display_name}",
            color=discord.Color.blue()
        )
        
        for match in history:
            p1_id, p2_id, winner_id, p1_score, p2_score, rounds, timestamp = match
            
            opponent_id = p2_id if p1_id == target.id else p1_id
            try:
                opponent = await self.client.fetch_user(opponent_id)
                opponent_name = opponent.display_name
            except:
                opponent_name = "Unknown"
                
            result = "🏆 Menang" if winner_id == target.id else "❌ Kalah" if winner_id else "🤝 Seri"
            score = f"{p1_score}-{p2_score}" if p1_id == target.id else f"{p2_score}-{p1_score}"
            
            embed.add_field(
                name=f"{result} vs {opponent_name}",
                value=f"Skor: {score} • {rounds} ronde",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(RPS(bot))
