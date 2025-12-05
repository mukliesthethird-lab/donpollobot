import httpx
import os
from typing import Optional, Dict

class TrackerValorantAPI:
    def __init__(self):
        self.api_key = os.getenv("TRACKER_API_KEY")
        self.base_url = "https://public-api.tracker.gg/v2/valorant/standard/profile/riot"

    async def get_stats(self, game_name: str, tag: str) -> Optional[Dict]:
        if not self.api_key:
            print("[Tracker API Error] API Key not found in environment variables.")
            return None

        riot_id_encoded = f"{game_name}%23{tag}"  # Encode '#' as %23
        url = f"{self.base_url}/{riot_id_encoded}"
        headers = {
            "TRN-Api-Key": self.api_key,
            "User-Agent": "ValorantDiscordBot/1.0"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[Tracker API Error] {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            print(f"[Exception] {e}")
            return None

# Fungsi wrapper agar bisa dipakai di cogs
async def get_valorant_stats(game_name: str, tag: str) -> Optional[Dict]:
    api = TrackerValorantAPI()
    raw_data = await api.get_stats(game_name, tag)
    
    if not raw_data or "data" not in raw_data:
        return None

    data = raw_data["data"]
    
    # Helper to safely get nested keys
    def get_val(obj, *keys, default="Unknown"):
        for key in keys:
            if isinstance(obj, dict):
                obj = obj.get(key, {})
            else:
                return default
        return obj if not isinstance(obj, dict) else default

    # Parsing Top Agents
    top_agents = []
    top_weapons = []
    top_maps = []
    
    if "segments" in data:
        # Agents
        agent_segments = [s for s in data["segments"] if s.get("type") == "agent"]
        agent_segments.sort(key=lambda x: x["stats"]["timePlayed"]["value"], reverse=True)
        for agent in agent_segments[:3]:
            name = agent["metadata"]["name"]
            playtime = agent["stats"]["timePlayed"]["displayValue"]
            top_agents.append(f"{name} ({playtime})")
            
        # Weapons
        weapon_segments = [s for s in data["segments"] if s.get("type") == "weapon"]
        weapon_segments.sort(key=lambda x: x["stats"]["kills"]["value"], reverse=True)
        if weapon_segments:
            top_weapon = weapon_segments[0]
            top_weapons = {
                "name": top_weapon["metadata"]["name"],
                "kills": top_weapon["stats"]["kills"]["displayValue"],
                "image": top_weapon["metadata"].get("imageUrl")
            }

        # Maps
        map_segments = [s for s in data["segments"] if s.get("type") == "map"]
        map_segments.sort(key=lambda x: x["stats"]["timePlayed"]["value"], reverse=True)
        if map_segments:
            top_map = map_segments[0]
            top_maps = {
                "name": top_map["metadata"]["name"],
                "win_rate": top_map["stats"]["matchesWinPct"]["displayValue"]
            }

    # Main Stats
    main_stats = data["segments"][0]["stats"]
    
    stats = {
        "current_rank": get_val(main_stats, "rank", "displayValue"),
        "peak_rank": get_val(main_stats, "peakRank", "displayValue", default="Unrated"),
        "win_rate": get_val(main_stats, "winRatio", "displayValue"),
        "kd_ratio": get_val(main_stats, "kd", "displayValue"),
        "headshot_percent": get_val(main_stats, "headshotPct", "displayValue"),
        "rank_image": get_val(main_stats, "rank", "metadata", "iconUrl"),
        "top_agents": top_agents,
        "top_weapon": top_weapons,
        "top_map": top_maps,
        "account_level": data.get("accountLevel", "Unknown")
    }

    return stats

async def get_mock_stats() -> Dict:
    """Returns dummy data for testing purposes"""
    return {
        "current_rank": "Radiant",
        "peak_rank": "Radiant #1",
        "win_rate": "65.5%",
        "kd_ratio": "1.45",
        "headshot_percent": "32.0%",
        "rank_image": "https://trackercdn.com/cdn/tracker.gg/valorant/icons/tiersv2/25.png",
        "account_level": "250",
        "top_agents": [
            "Jett (1200m)",
            "Reyna (800m)",
            "Omen (450m)"
        ],
        "top_weapon": {
            "name": "Vandal",
            "kills": "15,420",
            "image": "https://trackercdn.com/cdn/tracker.gg/valorant/db/weapons/vandal.png"
        },
        "top_map": {
            "name": "Ascent",
            "win_rate": "72%"
        }
    }

# Maintenance update
