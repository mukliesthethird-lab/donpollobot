import discord
from discord import app_commands
from discord.ext import commands
import aiohttp


def parse_emoji(raw: str):
    """Convert custom emoji '<:name:id>' into {'name': name, 'id': id}"""
    if isinstance(raw, dict):
        return raw  # already parsed
    
    if raw.startswith("<:") and raw.endswith(">"):
        # Example: <:mod:1440382534889377893>
        content = raw[2:-1]  # remove <:
        parts = content.split(":")  # ["mod", "144038..."]
        if len(parts) == 2:
            return {
                "name": parts[0],
                "id": parts[1]
            }
    
    # Unicode emoji → use name only
    return {"name": raw}


class Help(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Help Cog is ready')

    async def send_layoutview_message(self, interaction: discord.Interaction):
        """Send message with Components V2 using Container"""

        has_admin = interaction.user.guild_permissions.administrator
        
        # Define all categories
        categories = [
            {"label": "GENERAL", "emoji": "<:settings:1440385703417741352>", "custom_id": "help_cog_general"},
            {"label": "FUN", "emoji": "<:fun:1440388058284425309>", "custom_id": "help_cog_fun"},
            {"label": "MUSIC", "emoji": "<:music:1440387074397175940>", "custom_id": "help_cog_music"},
            {"label": "ECONOMY", "emoji": "💰", "custom_id": "help_cog_economy"},
            {"label": "GAMES", "emoji": "🎮", "custom_id": "help_cog_games"},
            {"label": "FISHING", "emoji": "🎣", "custom_id": "help_cog_fishing"},
        ]

        if has_admin:
            categories.insert(0, {
                "label": "MOD",
                "emoji": "<:mod:1440382534889377893>",
                "custom_id": "help_cog_moderation"
            })
        
        # Build button components (Split into rows if needed, max 5 per row)
        # Row 1
        row1_buttons = []
        for cat in categories[:4]: # First 4
            row1_buttons.append({
                "style": 2, "type": 2, "label": cat["label"], 
                "emoji": parse_emoji(cat["emoji"]), "custom_id": cat["custom_id"]
            })
            
        # Row 2
        row2_buttons = []
        for cat in categories[4:]: # Remaining
            row2_buttons.append({
                "style": 2, "type": 2, "label": cat["label"], 
                "emoji": parse_emoji(cat["emoji"]), "custom_id": cat["custom_id"]
            })

        # Invite button (Add to Row 2 or new Row)
        invite_btn = {
            "type": 2, "style": 5, "label": "INVITE BOT", "emoji": {"name": "🤖"},
            "url": f"https://discord.com/api/oauth2/authorize?client_id={self.client.user.id}&permissions=8&scope=bot%20applications.commands"
        }
        if len(row2_buttons) < 5:
            row2_buttons.append(invite_btn)
        else:
            # If row 2 full (unlikely here), handle it. But 7 items total fits in 2 rows.
            pass

        components_list = [
            {"type": 10, "content": "# Command Center\nPilih kategori di bawah untuk melihat daftar command.\n"},
            {"type": 14, "divider": True, "spacing": 1},
            {"type": 1, "components": row1_buttons}
        ]
        
        if row2_buttons:
            components_list.append({"type": 1, "components": row2_buttons})
            
        components_list.extend([
            {"type": 14},
            {
                "type": 9,
                "components": [
                    {"type": 10, "content": "**Masuk server developer**\nUntuk mendapatkan info terbaru.\n"}
                ],
                "accessory": {
                    "style": 5, "type": 2, "label": "JOIN SERVER",
                    "emoji": parse_emoji("<:join:1440388504818417795>"),
                    "url": "https://discord.gg/SuuQhTdwfa"
                }
            }
        ])

        payload = {
            "flags": 32768,
            "components": [{"type": 17, "spoiler": False, "components": components_list}]
        }

        # Send via API
        headers = {"Authorization": f"Bot {self.client.http.token}", "Content-Type": "application/json"}
        url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"

        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"type": 4, "data": payload}, headers=headers)

    @app_commands.command(name="help", description="Display bot command list")
    async def help(self, interaction: discord.Interaction):
        await self.send_layoutview_message(interaction)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button clicks from Container"""
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id.startswith("help_cog_"):
            cog_name_lower = custom_id.replace("help_cog_", "")
            
            # Map ID to Display Name
            name_map = {
                "moderation": "Moderation", "general": "General", "fun": "Fun",
                "music": "Music", "economy": "Economy", "games": "Games", "fishing": "Fishing"
            }
            cog_name = name_map.get(cog_name_lower, "General")
            
            command_lists = {
                "General": [
                    ("help", "Menampilkan daftar command bot"),
                    ("about", "Informasi tentang bot"),
                    ("avatar", "Menampilkan avatar user"),
                    ("invite", "Mendapatkan link invite bot"),
                    ("ping", "Mengecek latency bot"),
                    ("serverinfo", "Menampilkan informasi server"),
                    ("userinfo", "Menampilkan informasi user"),
                    ("kelamin", "Set gender role (Prefix Command: !kelamin)"),
                ],
                "Fun": [
                    ("roll", "Random Angka (0-100)"),
                    ("choose", "Biarkan BOT memilih"),
                    ("remind", "Mengatur Reminder"),
                ],
                "Music": [
                    ("play", "Memainkan musik dari youtube/spotify"),
                    ("lyrics", "Menampilkan Lirik"),
                    ("nowplaying", "Lagu yang sedang diputar"),
                    ("queue", "Antrian lagu"),
                    ("volume", "Mengatur suara"),
                    ("effect", "Efek suara (Bassboost, dll)"),
                    ("skip", "Skip lagu"),
                    ("leave", "Bot keluar voice channel"),
                ],
                "Economy": [
                    ("balance", "Cek saldo koin"),
                    ("pay", "Transfer koin ke user lain"),
                    ("daily", "Klaim bonus harian"),
                    ("work", "Bekerja untuk dapat koin"),
                    ("leaderboard", "Top global rich list"),
                    ("ngutang", "Pinjam koin (Jatuh tempo 24 jam)"),
                    ("pay_loan", "Bayar hutang"),
                ],
                "Games": [
                    ("pubg", "Cek stats PUBG (Steam/Console)"),
                    ("pubg_match", "Detail match terakhir PUBG"),
                    ("valorant", "Cek stats Valorant (Riot ID)"),
                    ("xox", "Main Tic-Tac-Toe (Bisa taruhan)"),
                    ("wl_setup", "Setup game Who's Lying (Admin)"),
                ],
                "Fishing": [
                    ("fish catch", "Memancing ikan"),
                    ("fish inventory", "Lihat hasil pancingan"),
                    ("fish leaderboard", "Leaderboard mancing"),
                    ("fish shop", "Beli pancingan"),
                    ("fish trade", "Trade ikan dengan teman"),
                    ("fishing_rod", "Ganti pancingan"),
                    ("fish shop", "Beli pancingan baru"),

                ],
                "Moderation": [
                    ("ban", "Ban user"),
                    ("kick", "Kick user"),
                    ("mute", "Mute user"),
                    ("warn", "Warn user"),
                    ("purge", "Hapus pesan massal"),
                    ("poll", "Buat voting"),
                    ("ticket-setup", "Setup sistem tiket support"),
                ],
            }

            # Rebuild buttons to show selection state
            categories = [
                {"label": "MOD", "emoji": "<:mod:1440382534889377893>", "custom_id": "help_cog_moderation"},
                {"label": "GENERAL", "emoji": "<:settings:1440385703417741352>", "custom_id": "help_cog_general"},
                {"label": "FUN", "emoji": "<:fun:1440388058284425309>", "custom_id": "help_cog_fun"},
                {"label": "MUSIC", "emoji": "<:music:1440387074397175940>", "custom_id": "help_cog_music"},
                {"label": "ECONOMY", "emoji": "💰", "custom_id": "help_cog_economy"},
                {"label": "GAMES", "emoji": "🎮", "custom_id": "help_cog_games"},
                {"label": "FISHING", "emoji": "🎣", "custom_id": "help_cog_fishing"},
            ]
            
            # Filter MOD if not admin (optional check, but good for consistency)
            # For simplicity in update, we show all or check permissions again.
            # Since interaction is ephemeral update, we can just rebuild all.
            
            row1_buttons = []
            for cat in categories[:4]:
                style = 3 if cat["custom_id"] == custom_id else 2
                row1_buttons.append({
                    "style": style, "type": 2, "label": cat["label"], 
                    "emoji": parse_emoji(cat["emoji"]), "custom_id": cat["custom_id"]
                })
                
            row2_buttons = []
            for cat in categories[4:]:
                style = 3 if cat["custom_id"] == custom_id else 2
                row2_buttons.append({
                    "style": style, "type": 2, "label": cat["label"], 
                    "emoji": parse_emoji(cat["emoji"]), "custom_id": cat["custom_id"]
                })
                
            invite_btn = {
                "type": 2, "style": 5, "label": "INVITE BOT", "emoji": {"name": "🤖"},
                "url": f"https://discord.com/api/oauth2/authorize?client_id={self.client.user.id}&permissions=8&scope=bot%20applications.commands"
            }
            if len(row2_buttons) < 5:
                row2_buttons.append(invite_btn)

            if cog_name in command_lists:
                cmd_list = "\n".join([f"**/{cmd_name}** - {cmd_desc}" for cmd_name, cmd_desc in command_lists[cog_name]])

                components_list = [
                    {"type": 10, "content": f"# Command Center - {cog_name}\nBerikut adalah daftar commands untuk kategori ini:\n"},
                    {"type": 14, "divider": True, "spacing": 1},
                    {"type": 1, "components": row1_buttons}
                ]
                if row2_buttons:
                    components_list.append({"type": 1, "components": row2_buttons})
                    
                components_list.extend([
                    {"type": 14},
                    {"type": 10, "content": f"## Available Commands:\n\n{cmd_list}\n"},
                    {"type": 14},
                    {
                        "type": 9,
                        "components": [{"type": 10, "content": "**Masuk server developer**\nUntuk mendapatkan info terbaru.\n"}],
                        "accessory": {
                            "style": 5, "type": 2, "label": "JOIN SERVER",
                            "emoji": parse_emoji("<:join:1440388504818417795>"),
                            "url": "https://discord.gg/SuuQhTdwfa"
                        }
                    }
                ])

                payload = {
                    "flags": 32768,
                    "components": [{"type": 17, "spoiler": False, "components": components_list}]
                }

                headers = {"Authorization": f"Bot {self.client.http.token}", "Content-Type": "application/json"}
                url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"

                async with aiohttp.ClientSession() as session:
                    await session.post(url, json={"type": 7, "data": payload}, headers=headers)
            else:
                await interaction.response.send_message(f"❌ No commands available for '{cog_name}' category!", ephemeral=True)

async def setup(client: commands.Bot):
    await client.add_cog(Help(client))
    
# Maintenance update
