import discord
from discord.ext import commands
from discord import app_commands
from utils.pubg_api import get_pubg_stats, get_last_match
import aiohttp
import json
import asyncio

class PubgStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def build_match_payload(self, match: dict = None, loading: bool = False):
        """Builds the raw JSON payload for the match details container"""
        
        if loading:
            container_components = [
                {"type": 10, "content": "# 🔄 Fetching Last Match...\nPlease wait a moment."},
                {"type": 14, "divider": True, "spacing": 1}
            ]
        else:
            # 1. Header & Map Image
            # Using Markdown image syntax for the map
            header_content = (
                f"# Match Details: {match['map_name']}\n"
                f"**Mode**: {match['mode'].upper()} | **Duration**: {match['duration']} | **Date**: {match['date']}\n"
            )
            
            container_components = [
                {"type": 10, "content": header_content},
                {"type": 14, "divider": True, "spacing": 1},
                {"type": 14, "spacing": 1}
            ]

            # 2. Player Performance
            s = match['stats']
            performance_content = (
                f"## {match['username']}'s Performance\n"
                f">>> `🏆 Rank: #{match['rank']}` `💀 Kills: {s['kills']}` `💥 Damage: {s['damage']}`\n"
                f"`🤕 Assists: {s['assists']}` `😵 DBNOs: {s['dbnos']}` `🏃 Distance: {s['distance']}`\n"
                f"`⏱️ Survived: {s['time_survived']}`\n"
            )
            container_components.append({"type": 10, "content": performance_content})
            container_components.append({"type": 14, "spacing": 1})

            # 3. Teammates (Roster)
            if match['teammates']:
                teammates_content = "## Teammates\n"
                for t in match['teammates']:
                    teammates_content += f"- **{t['name']}**: `💀 {t['kills']}` `💥 {int(t['damageDealt'])}`\n"
                container_components.append({"type": 10, "content": teammates_content})
                container_components.append({"type": 14, "spacing": 1})

            # 4. Action Buttons
            action_row = {
                "type": 1,
                "components": [
                    {
                        "type": 2, "style": 5, "label": "View on Tracker.gg", "emoji": {"name": "🔗"}, 
                        "url": f"https://tracker.gg/pubg/profile/{match['platform']}/{match['username']}/matches"
                    },
                    {
                        "type": 2, "style": 4, "label": "Delete", "emoji": {"name": "🗑️"}, 
                        "custom_id": "pubg_delete"
                    }
                ]
            }
            container_components.append(action_row)
            
            # 5. Footer
            footer_component = {
                "type": 9,
                "components": [
                    {"type": 10, "content": "Match data provided by **Official PUBG API**"}
                ],
                "accessory": {
                    "type": 2, "style": 5, "label": "API", 
                    "url": "https://documentation.pubg.com/en/index.html",
                    "emoji": {"name": "🌐"}
                }
            }
            container_components.append(footer_component)

        return {
            "flags": 32768, 
            "components": [
                {"type": 14}, 
                {
                    "type": 17,
                    "spoiler": False,
                    "components": container_components
                }
            ]
        }

    def build_pubg_payload(self, stats: dict = None, loading: bool = False, tab: str = "overview"):
        """Builds the raw JSON payload for the container with Tabs"""
        
        if loading:
            container_components = [
                {"type": 10, "content": "# 🔄 Fetching PUBG Stats...\nPlease wait a moment."},
                {"type": 14, "divider": True, "spacing": 1}
            ]
        else:
            # 1. Header
            header_content = f"# PUBG STATS: {stats['username']}\nPlatform: **{stats['platform'].upper()}**"
            
            container_components = [
                {"type": 10, "content": header_content},
                {"type": 14, "divider": True, "spacing": 1},
            ]

            # 2. Tab Buttons (Moved to Top)
            tab_buttons = {
                "type": 1,
                "components": [
                    {
                        "type": 2, "style": 2 if tab != "overview" else 1, "label": "Overview", 
                        "custom_id": f"pubg_tab:overview:{stats['username']}:{stats['platform']}"
                    },
                    {
                        "type": 2, "style": 2 if tab != "tpp" else 1, "label": "TPP Stats", 
                        "custom_id": f"pubg_tab:tpp:{stats['username']}:{stats['platform']}"
                    },
                    {
                        "type": 2, "style": 2 if tab != "fpp" else 1, "label": "FPP Stats", 
                        "custom_id": f"pubg_tab:fpp:{stats['username']}:{stats['platform']}"
                    }
                ]
            }
            container_components.append(tab_buttons)
            container_components.append({"type": 14, "spacing": 1})

            # 3. Content
            if tab == "overview":
                s = stats['overview']
                # Removed invisible separators
                stats_content = (
                    f"# Overview ({s['mode_name'].upper()})\n\n"
                    f"## >>> `🏆 Win: {s['wins']}` `🔝 Top 10: {s['top10s']}` `📊 Win Rate: {s['win_rate']}`\n"
                    f"`🔫 K/D: {s['kd']}` `💀 Kills: {s['kills']}` `🤕 Assists: {s['assists']}`\n"
                    f"`🎯 Headshots: {s['headshot_kills']}` `📏 Longest Kill: {s['longest_kill']}`\n"
                    f"`💥 Avg Dmg: {s['avg_damage']}` `💊 Heals: {s['heals']}`\n\n\n"
                )
                container_components.append({"type": 10, "content": stats_content})
                
            elif tab in ["fpp", "tpp"]:
                modes = stats[tab]
                content = f"# {tab.upper()} Stats\n\n"
                
                for mode_name in ["solo", "duo", "squad"]:
                    m = modes[mode_name]
                    if m['matches'] > 0:
                        # Removed >>> and invisible separators
                        content += (
                            f"## {mode_name.upper()}\n"
                            f"`🏆 Win: {m['wins']}` `🔫 K/D: {m['kd']}` `📊 WR: {m['win_rate']}`\n"
                            f"`💀 Kills: {m['kills']}` `💥 Dmg: {m['avg_damage']}`\n\n"
                        )
                    else:
                        content += f"## {mode_name.upper()}\n*No matches played*\n\n"
                
                container_components.append({"type": 10, "content": content})

            container_components.append({"type": 14, "spacing": 1})

            # 4. Action Buttons (Refresh/Link)
            action_row = {
                "type": 1,
                "components": [
                    {
                        "type": 2, "style": 3, "label": "Refresh", "emoji": {"name": "🔄"}, 
                        "custom_id": f"pubg_refresh:{stats['username']}:{stats['platform']}"
                    },
                    {
                        "type": 2, "style": 5, "label": "Tracker.gg", "emoji": {"name": "🔗"}, 
                        "url": f"https://tracker.gg/pubg/profile/{stats['platform']}/{stats['username']}/overview"
                    },
                    {
                        "type": 2, "style": 4, "label": "Delete", "emoji": {"name": "🗑️"}, 
                        "custom_id": "pubg_delete"
                    }
                ]
            }
            container_components.append(action_row)
            container_components.append({"type": 14, "spacing": 1})
            
            # 5. Footer
            footer_component = {
                "type": 9,
                "components": [
                    {"type": 10, "content": "Stats provided by **Official PUBG API**"}
                ],
                "accessory": {
                    "type": 2, "style": 5, "label": "API", 
                    "url": "https://documentation.pubg.com/en/index.html",
                    "emoji": {"name": "🌐"}
                }
            }
            container_components.append(footer_component)

        return {
            "flags": 32768, 
            "components": [
                {"type": 14}, # Top Spacer as requested
                {
                    "type": 17,
                    "spoiler": False,
                    "components": container_components
                }
            ]
        }

    async def send_initial_loading(self, interaction: discord.Interaction):
        """Sends the initial 'Loading' response (Type 4)"""
        payload = self.build_pubg_payload(loading=True)
        
        url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            callback_payload = {"type": 4, "data": payload}
            async with session.post(url, json=callback_payload, headers=headers) as resp:
                if resp.status not in [200, 204]:
                    print(f"❌ Error sending loading state: {resp.status} {await resp.text()}")
                    return False
        return True

    async def update_pubg_message(self, interaction: discord.Interaction, stats: dict, tab: str = "overview"):
        """Updates the original message via Webhook (PATCH)"""
        payload = self.build_pubg_payload(stats=stats, loading=False, tab=tab)
        
        # Use Webhook endpoint to edit the original message
        url = f"https://discord.com/api/v10/webhooks/{self.bot.user.id}/{interaction.token}/messages/@original"
        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=payload, headers=headers) as resp:
                if resp.status not in [200, 204]:
                    print(f"❌ Error updating PUBG message: {resp.status} {await resp.text()}")

    @app_commands.command(name="pubg", description="Cek stats PUBG pemain (Components V2)")
    @app_commands.describe(username="Username PUBG", platform="Platform (steam, kakao, xbox, psn)")
    async def pubg_stats(self, interaction: discord.Interaction, username: str, platform: str = "steam"):
        # 1. Send Loading State immediately
        if not await self.send_initial_loading(interaction):
            return # Failed to send initial response
            
        try:
            # 2. Fetch Stats
            stats = await get_pubg_stats(username, platform)
            
            if not stats:
                # Update with error message
                error_payload = {
                    "content": "❌ Pemain tidak ditemukan atau API Key salah.",
                    "components": [] # Clear components
                }
                url = f"https://discord.com/api/v10/webhooks/{self.bot.user.id}/{interaction.token}/messages/@original"
                headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
                async with aiohttp.ClientSession() as session:
                    await session.patch(url, json=error_payload, headers=headers)
                return

            # 3. Update with Real Stats (Default Tab: Overview)
            await self.update_pubg_message(interaction, stats, tab="overview")
            
        except Exception as e:
            print(f"Error PUBG: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button clicks for PUBG components"""
        if interaction.type != discord.InteractionType.component:
            return
            
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id == "pubg_delete":
            await interaction.message.delete()
            
        elif custom_id.startswith("pubg_refresh:"):
            try:
                _, username, platform = custom_id.split(":")
                
                # Defer Update (Type 6)
                url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
                headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
                async with aiohttp.ClientSession() as session:
                    await session.post(url, json={"type": 6}, headers=headers)
                
                # Fetch and Edit
                stats = await get_pubg_stats(username, platform, force_refresh=True)
                if stats:
                    await self.update_pubg_message(interaction, stats, tab="overview") # Reset to overview on refresh
                    
            except Exception as e:
                print(f"Error refreshing PUBG: {e}")

        elif custom_id.startswith("pubg_tab:"):
            # Format: pubg_tab:mode:username:platform
            try:
                _, tab_mode, username, platform = custom_id.split(":")
                
                # Defer Update (Type 6)
                url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
                headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
                async with aiohttp.ClientSession() as session:
                    await session.post(url, json={"type": 6}, headers=headers)

                # Fetch (Cached) and Edit with new Tab
                stats = await get_pubg_stats(username, platform)
                if stats:
                    await self.update_pubg_message(interaction, stats, tab=tab_mode)
                    
            except Exception as e:
                print(f"Error switching PUBG tab: {e}")

    @app_commands.command(name="pubg_match", description="Cek detail match terakhir pemain")
    @app_commands.describe(username="Username PUBG", platform="Platform (steam, kakao, xbox, psn)")
    async def pubg_match(self, interaction: discord.Interaction, username: str, platform: str = "steam"):
        # 1. Send Loading State
        payload = self.build_match_payload(loading=True)
        url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"type": 4, "data": payload}, headers=headers)
            
            # 2. Fetch Match Data
            match_data = await get_last_match(username, platform)
            
            webhook_url = f"https://discord.com/api/v10/webhooks/{self.bot.user.id}/{interaction.token}/messages/@original"
            
            if not match_data:
                error_payload = {
                    "content": "❌ Match tidak ditemukan atau API Key salah.",
                    "components": []
                }
                await session.patch(webhook_url, json=error_payload, headers=headers)
                return

            # 3. Update with Match Details
            final_payload = self.build_match_payload(match=match_data, loading=False)
            async with session.patch(webhook_url, json=final_payload, headers=headers) as resp:
                if resp.status not in [200, 204]:
                    print(f"❌ Error updating match message: {resp.status} {await resp.text()}")
                    # Fallback: Send error message to user
                    await session.patch(webhook_url, json={"content": f"❌ Error: {resp.status} - Invalid Payload"}, headers=headers)

async def setup(bot: commands.Bot):
    await bot.add_cog(PubgStats(bot))
