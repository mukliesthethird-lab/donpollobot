import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp
import asyncio

class Slot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.symbols = ["🍒", "🍋", "🍇", "🍊", "🍉", "💎", "⭐"]

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Slot Cog is ready')

    def get_economy(self):
        return self.bot.get_cog('Economy')

    def build_slot_payload(self, slots: list, result_text: str, balance: int, bet: int, win_amount: int):
        # Header
        header_content = "# SLOT MACHINE"
        
        # Status
        status_content = f"## 💰 Bet: {bet} 🏦 Balance: {balance}"
        
        # Slot Reels (Buttons)
        reel_components = []
        for symbol in slots:
            reel_components.append({
                "type": 2,
                "style": 2, # Secondary/Grey
                "emoji": {"name": symbol},
                "disabled": True,
                "custom_id": f"slot_reel_{random.randint(1000,9999)}" # Random ID to avoid conflicts
            })
            
        # Result
        if win_amount > 0:
            footer_content = f"## 🎉 {result_text}\n# +{win_amount} coins!"
        else:
            footer_content = f"## 💸 {result_text}\n# -{bet} coins"

        return {
            "flags": 32768, # Ephemeral-like
            "components": [
                {
                    "type": 17,
                    "components": [
                        {"type": 10, "content": header_content},
                        {"type": 14, "spacing": 1},
                        {"type": 10, "content": status_content},
                        {"type": 14, "spacing": 1},
                        {
                            "type": 1,
                            "components": reel_components
                        },
                        {"type": 14, "spacing": 1},
                        {"type": 10, "content": footer_content}
                    ]
                }
            ]
        }

    async def send_raw_payload(self, interaction: discord.Interaction, payload: dict):
        url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            # Type 4 = Channel Message with Source
            json_data = {"type": 4, "data": payload}
            async with session.post(url, json=json_data, headers=headers) as resp:
                if resp.status not in [200, 204]:
                    print(f"❌ Error sending Slot payload: {resp.status} {await resp.text()}")

    @app_commands.command(name="slot", description="Mainkan mesin slot dengan taruhan! (Components V2)")
    @app_commands.describe(bet="Jumlah taruhan (default: 10)")
    async def slot(self, interaction: discord.Interaction, bet: int = 10):
        economy = self.get_economy()
        if not economy:
            await interaction.response.send_message("❌ Sistem ekonomi belum dimuat!", ephemeral=True)
            return

        user_id = interaction.user.id
        current_balance = economy.get_balance(user_id)

        # Validasi taruhan
        if bet < 1:
            await interaction.response.send_message("❌ Taruhan minimal 1 koin!", ephemeral=True)
            return

        if bet > current_balance:
            await interaction.response.send_message(f"❌ Saldo tidak cukup! (Butuh: {bet}, Ada: {current_balance})", ephemeral=True)
            return

        # Putar slot
        slot1 = random.choice(self.symbols)
        slot2 = random.choice(self.symbols)
        slot3 = random.choice(self.symbols)
        slots = [slot1, slot2, slot3]

        # Hitung kemenangan
        winnings = 0
        result_text = ""
        
        if slot1 == slot2 == slot3:
            if slot1 == "💎":
                winnings = bet * 20
                result_text = "DIAMOND JACKPOT!"
            elif slot1 == "⭐":
                winnings = bet * 15
                result_text = "STAR JACKPOT!"
            else:
                winnings = bet * 10
                result_text = "JACKPOT!"
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            winnings = int(bet * 1.5)
            result_text = "DOUBLE MATCH!"
        else:
            winnings = -bet
            result_text = "LOSE!"

        # Update balance
        new_balance = economy.update_balance(user_id, winnings)

        # Build and send payload
        payload = self.build_slot_payload(slots, result_text, new_balance, bet, winnings)
        await self.send_raw_payload(interaction, payload)



async def setup(bot):
    await bot.add_cog(Slot(bot))
