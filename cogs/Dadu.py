import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import aiohttp

class Dadu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}

    def get_economy(self):
        return self.bot.get_cog('Economy')

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Dadu Cog is ready')

    def build_dadu_payload(self, title: str, status: str, dice_results: list, result_text: str, loading: bool = False):
        # Header
        header_content = f"# {title}\n"
        
        # Status (Players / Bet)
        status_content = f"## {status}"

        container_items = [
            {"type": 10, "content": header_content},
            {"type": 14, "spacing": 1},
            {"type": 10, "content": status_content},
            {"type": 14, "spacing": 1}
        ]

        if loading:
             container_items.append({"type": 10, "content": "### 🎲 Rolling the dice..."})
        else:
            # Dice Components (Buttons)
            # Max 5 per row.
            rows = []
            current_row = []
            
            for i, roll in enumerate(dice_results):
                btn = {
                    "type": 2,
                    "style": 2, # Secondary/Grey
                    "label": str(roll),
                    "emoji": {"name": "🎲"},
                    "disabled": True,
                    "custom_id": f"dice_{i}_{random.randint(1000,9999)}"
                }
                current_row.append(btn)
                
                if len(current_row) == 5:
                    rows.append({"type": 1, "components": current_row})
                    current_row = []
            
            if current_row:
                rows.append({"type": 1, "components": current_row})
            
            # Add dice rows
            for row in rows:
                container_items.append(row)
                
            container_items.append({"type": 14, "spacing": 1})
            container_items.append({"type": 10, "content": f"## {result_text}"})

        return {
            "flags": 32768, # Required for Components V2 (Type 17)
            "components": [
                {"type": 14}, # Top Spacer
                {
                    "type": 17,
                    "spoiler": False,
                    "components": container_items
                }
            ]
        }

    async def send_raw_payload(self, interaction: discord.Interaction, payload: dict, edit: bool = False):
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
                    print(f"❌ Error sending Dadu payload: {resp.status} {await resp.text()}")

    @app_commands.command(name="dadu", description="Lempar dadu! Main sendiri, lawan teman, atau dengan taruhan.")
    @app_commands.describe(
        bet="Jumlah taruhan (Wajib tag lawan jika mengisi ini)",
        opponent="Lawan main (Opsional)",
        amount="Jumlah dadu (Default: 1, Max: 10)",
        sides="Jumlah sisi dadu (Default: 6)"
    )
    async def dadu(self, interaction: discord.Interaction, bet: int = 0, opponent: discord.Member = None, amount: int = 1, sides: int = 6):
        # 1. Validasi Input
        if amount < 1 or amount > 10:
            await interaction.response.send_message("❌ Jumlah dadu harus 1-10!", ephemeral=True)
            return
        if sides < 2 or sides > 100:
            await interaction.response.send_message("❌ Sisi dadu harus 2-100!", ephemeral=True)
            return
        if bet > 0 and opponent is None:
            await interaction.response.send_message("❌ **Error:** Jika bet, wajib tag lawan!", ephemeral=True)
            return

        # 2. Mode Solo
        if opponent is None:
            # Send Loading State (Type 4)
            loading_payload = self.build_dadu_payload(
                title="🎲 SOLO ROLL 🎲",
                status=f"👤 {interaction.user.display_name}",
                dice_results=[],
                result_text="",
                loading=True
            )
            await self.send_raw_payload(interaction, loading_payload, edit=False)
            
            await asyncio.sleep(1)

            results = [random.randint(1, sides) for _ in range(amount)]
            total = sum(results)
            
            payload = self.build_dadu_payload(
                title="🎲 SOLO ROLL 🎲",
                status=f"👤 {interaction.user.display_name}",
                dice_results=results,
                result_text=f"Total: {total}"
            )
            await self.send_raw_payload(interaction, payload, edit=True)
            return

        # 3. Mode Duel
        if opponent.id == interaction.user.id or opponent.bot:
            await interaction.response.send_message("❌ Lawan tidak valid!", ephemeral=True)
            return

        # Cek Ekonomi
        if bet > 0:
            economy = self.get_economy()
            if not economy:
                await interaction.response.send_message("❌ Ekonomi error!", ephemeral=True)
                return
            
            if economy.get_balance(interaction.user.id) < bet:
                await interaction.response.send_message(f"❌ Saldo Anda kurang!", ephemeral=True)
                return
            if economy.get_balance(opponent.id) < bet:
                await interaction.response.send_message(f"❌ Saldo lawan kurang!", ephemeral=True)
                return

        # Loading Duel (Type 4)
        header_text = f"⚔️ DUEL: {interaction.user.display_name} vs {opponent.display_name}"
        if bet > 0: header_text += f" | Bet: {bet}"
        
        loading_payload = self.build_dadu_payload(
            title=header_text,
            status="Preparing duel...",
            dice_results=[],
            result_text="",
            loading=True
        )
        await self.send_raw_payload(interaction, loading_payload, edit=False)
        
        await asyncio.sleep(2)
        
        # Roll
        p1_results = [random.randint(1, sides) for _ in range(amount)]
        p1_total = sum(p1_results)
        
        p2_results = [random.randint(1, sides) for _ in range(amount)]
        p2_total = sum(p2_results)

        # Winner
        if p1_total > p2_total:
            winner = interaction.user
            loser = opponent
            res_text = f"🏆 {winner.display_name} WINS!"
        elif p2_total > p1_total:
            winner = opponent
            loser = interaction.user
            res_text = f"🏆 {winner.display_name} WINS!"
        else:
            winner = None
            res_text = "🤝 DRAW!"

        # Money
        if bet > 0 and winner:
            economy.transfer_money(loser.id, winner.id, bet)
            res_text += f"\n💰 Won {bet} coins!"
        elif bet > 0:
            res_text += "\n💰 Bet returned."

        # Custom Payload Construction for Duel (Final)
        header = f"# {header_text}"
        
        # Helper to split into rows
        def create_dice_rows(results, prefix):
            rows = []
            current_row = []
            for i, r in enumerate(results):
                current_row.append({
                    "type": 2, 
                    "style": 1 if prefix == "d1" else 4, 
                    "label": str(r), 
                    "emoji": {"name": "🎲"}, 
                    "disabled": True, 
                    "custom_id": f"{prefix}_{random.randint(1,9999)}_{i}"
                })
                if len(current_row) == 5:
                    rows.append({"type": 1, "components": current_row})
                    current_row = []
            if current_row:
                rows.append({"type": 1, "components": current_row})
            return rows

        p1_rows = create_dice_rows(p1_results, "d1")
        p2_rows = create_dice_rows(p2_results, "d2")

        container = [
            {"type": 10, "content": header},
            {"type": 14, "spacing": 1},
            {"type": 10, "content": f"## 👤 {interaction.user.display_name}: {p1_total}"}
        ]
        
        container.extend(p1_rows)
        
        container.extend([
            {"type": 14, "spacing": 1},
            {"type": 10, "content": f"## 👤 {opponent.display_name}: {p2_total}"}
        ])
        
        container.extend(p2_rows)
        
        container.extend([
            {"type": 14, "spacing": 1},
            {"type": 10, "content": f"# {res_text}"}
        ])

        payload = {
            "flags": 32768,
            "components": [
                {"type": 14}, # Top Spacer
                {
                    "type": 17, 
                    "spoiler": False,
                    "components": container
                }
            ]
        }
        
        await self.send_raw_payload(interaction, payload, edit=True)

async def setup(bot):
    await bot.add_cog(Dadu(bot))
