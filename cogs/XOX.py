import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import asyncio
from typing import List, Optional, Dict

class XOXGame:
    def __init__(self, player1: discord.Member, bet: int = 0):
        self.player1 = player1
        self.player2: Optional[discord.Member] = None
        self.bet = bet
        self.board = ["BLANK"] * 9  # 0-8, BLANK, X, O
        self.turn = player1
        self.winner: Optional[discord.Member] = None
        self.is_draw = False
        self.is_active = True

    def join(self, player2: discord.Member) -> bool:
        if self.player2 is None and player2.id != self.player1.id:
            self.player2 = player2
            return True
        return False

    def make_move(self, player: discord.Member, position: int) -> bool:
        if not self.is_active or self.player2 is None:
            return False
        if player.id != self.turn.id:
            return False
        if 0 <= position < 9 and self.board[position] == "BLANK":
            symbol = "X" if player.id == self.player1.id else "O"
            self.board[position] = symbol
            if self.check_win(symbol):
                self.winner = player
                self.is_active = False
            elif "BLANK" not in self.board:
                self.is_draw = True
                self.is_active = False
            else:
                self.turn = self.player2 if self.turn == self.player1 else self.player1
            return True
        return False

    def check_win(self, symbol: str) -> bool:
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Rows
            (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Cols
            (0, 4, 8), (2, 4, 6)              # Diagonals
        ]
        return any(all(self.board[i] == symbol for i in line) for line in wins)

class XOX(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games: Dict[int, XOXGame] = {} # Message ID -> Game

    def get_economy(self):
        return self.bot.get_cog('Economy')

    def build_payload(self, game: XOXGame):
        # Header
        header_content = "# TIC TAC TOE\n"
        
        # Player Status
        p1_mention = game.player1.mention
        p2_mention = game.player2.mention if game.player2 else "Waiting..."
        status_content = f"# {p1_mention} VS {p2_mention}"

        # Board Components
        # We map board index 0-8 to the 3 rows of components
        board_components = []
        
        for row in range(3):
            row_components = []
            for col in range(3):
                index = row * 3 + col
                cell = game.board[index]
                
                # Determine Style and Emoji based on cell state
                if cell == "X":
                    style = 1 # Blue/Primary
                    emoji = {"name": "❌"}
                    disabled = True
                elif cell == "O":
                    style = 3 # Green/Success
                    emoji = {"name": "⭕"}
                    disabled = True
                else:
                    style = 2 # Grey/Secondary
                    emoji = {"name": "🔲"}
                    disabled = False

                # Disable all if game over or waiting for player
                if not game.is_active or game.player2 is None:
                    disabled = True

                btn = {
                    "type": 2,
                    "style": style,
                    "custom_id": f"xox_move_{index}",
                    "emoji": emoji,
                    "disabled": disabled
                }
                row_components.append(btn)
            
            board_components.append({
                "type": 1,
                "components": row_components
            })

        # Turn Indicator or Result
        if game.winner:
            footer_text = f"## 🏆 WINNER: {game.winner.mention}!"
            if game.bet > 0:
                footer_text += f"\n💰 Won {game.bet} coins!"
        elif game.is_draw:
            footer_text = "## 🤝 DRAW!"
        elif game.player2 is None:
            footer_text = "## ⏳ Waiting for opponent..."
        else:
            footer_text = f"Turn: \n## {game.turn.mention}"

        # Construct Container Components
        container_items = [
            {"type": 10, "content": header_content},
            {"type": 14, "spacing": 1}, # Spacer
            {"type": 10, "content": status_content},
            {"type": 14, "spacing": 1}, # Spacer
        ]
        
        # Add Board Rows
        for row_comp in board_components:
            container_items.append(row_comp)
            
        container_items.append({"type": 14, "spacing": 1}) # Spacer
        container_items.append({"type": 10, "content": footer_text})

        # Join Button (if waiting)
        if game.player2 is None:
            container_items.insert(1, {
                "type": 1,
                "components": [{
                    "type": 2,
                    "style": 3, # Green
                    "label": "JOIN GAME",
                    "emoji": {"name": "✏️"},
                    "custom_id": "xox_join"
                }]
            })
            container_items.insert(2, {"type": 14, "spacing": 1})

        return {
            "flags": 32768, # Ephemeral-like flag often used in these payloads
            "components": [
                {
                    "type": 17,
                    "components": container_items
                }
            ]
        }

    async def send_raw_payload(self, interaction: discord.Interaction, payload: dict, edit: bool = False):
        """Helper to send raw JSON payload"""
        if edit:
            url = f"https://discord.com/api/v10/webhooks/{self.bot.user.id}/{interaction.token}/messages/@original"
            method = "PATCH"
        else:
            url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
            method = "POST"
            payload = {"type": 4, "data": payload}

        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=payload, headers=headers) as resp:
                if resp.status not in [200, 204]:
                    print(f"❌ Error sending XOX payload: {resp.status} {await resp.text()}")
                    return False
        return True

    @app_commands.command(name="xox", description="Mainkan XOX (Tic-Tac-Toe) dengan taruhan!")
    @app_commands.describe(bet="Jumlah taruhan (opsional)")
    async def xox(self, interaction: discord.Interaction, bet: int = 0):
        # Economy Check
        if bet > 0:
            economy = self.get_economy()
            if not economy:
                await interaction.response.send_message("❌ Sistem ekonomi belum siap!", ephemeral=True)
                return
            
            bal = economy.get_balance(interaction.user.id)
            if bal < bet:
                await interaction.response.send_message(f"❌ Saldo tidak cukup! (Butuh: {bet}, Ada: {bal})", ephemeral=True)
                return

        game = XOXGame(interaction.user, bet)
        # We need to send the initial message to get the ID, but we can't get ID from interaction response easily without fetching.
        # So we send the payload, then fetch the original message to store the game state.
        
        payload = self.build_payload(game)
        if await self.send_raw_payload(interaction, payload):
            # Fetch original message to map ID
            msg = await interaction.original_response()
            self.games[msg.id] = game

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
            
        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("xox_"):
            return

        msg_id = interaction.message.id
        game = self.games.get(msg_id)

        if not game:
            # Try to recover game state or just ignore (could be old game)
            await interaction.response.send_message("❌ Permainan ini sudah berakhir atau kadaluarsa.", ephemeral=True)
            return

        if custom_id == "xox_join":
            if game.player2:
                await interaction.response.send_message("❌ Permainan sudah penuh!", ephemeral=True)
                return
            
            if interaction.user.id == game.player1.id:
                await interaction.response.send_message("❌ Anda tidak bisa melawan diri sendiri!", ephemeral=True)
                return

            # Economy Check for P2
            if game.bet > 0:
                economy = self.get_economy()
                if economy:
                    bal = economy.get_balance(interaction.user.id)
                    if bal < game.bet:
                        await interaction.response.send_message(f"❌ Saldo tidak cukup! (Butuh: {game.bet}, Ada: {bal})", ephemeral=True)
                        return

            game.join(interaction.user)
            # Update message
            payload = self.build_payload(game)
            # We must acknowledge the interaction. We can use Update Message (Type 7)
            
            url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
            headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={"type": 7, "data": payload}, headers=headers)

        elif custom_id.startswith("xox_move_"):
            try:
                pos = int(custom_id.split("_")[-1])
            except:
                return

            if interaction.user.id != game.turn.id:
                await interaction.response.send_message("❌ Bukan giliran Anda!", ephemeral=True)
                return

            if game.make_move(interaction.user, pos):
                # Check win/draw for economy
                if not game.is_active:
                    if game.winner and game.bet > 0:
                        economy = self.get_economy()
                        if economy:
                            loser = game.player2 if game.winner.id == game.player1.id else game.player1
                            # Transfer money
                            economy.transfer_money(loser.id, game.winner.id, game.bet)
                    
                    # Remove game from memory
                    del self.games[msg_id]

                payload = self.build_payload(game)
                
                # Update Message (Type 7)
                url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
                headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
                async with aiohttp.ClientSession() as session:
                    await session.post(url, json={"type": 7, "data": payload}, headers=headers)
            else:
                 await interaction.response.send_message("❌ Langkah tidak valid!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(XOX(bot))
