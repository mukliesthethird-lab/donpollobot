import httpx
import os
import time
from typing import Dict, Optional

# Simple in-memory cache: { "username:platform": (timestamp, data) }
_PUBG_CACHE = {}
CACHE_TTL = 600  # 10 minutes in seconds

def _get_weapon_image(weapon_id: str) -> str:
    """Returns an image URL for a given weapon ID"""
    # Common PUBG Weapons
    weapons = {
        "Item_Weapon_M416_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/6/62/M416_Icon.png",
        "Item_Weapon_AK47_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/1/1b/AKM_Icon.png",
        "Item_Weapon_SCAR-L_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/c/c9/SCAR-L_Icon.png",
        "Item_Weapon_BerylM762_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/2/26/Beryl_M762_Icon.png",
        "Item_Weapon_Kar98k_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/7/7b/Kar98k_Icon.png",
        "Item_Weapon_M24_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/0/00/M24_Icon.png",
        "Item_Weapon_AWM_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/4/46/AWM_Icon.png",
        "Item_Weapon_Mini14_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/c/c1/Mini_14_Icon.png",
        "Item_Weapon_SKS_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/3/39/SKS_Icon.png",
        "Item_Weapon_QBU88_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/e/e3/QBU_Icon.png",
        "Item_Weapon_Mk12_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/0/06/Mk12_Icon.png",
        "Item_Weapon_UMP_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/d/da/UMP45_Icon.png",
        "Item_Weapon_Vector_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/8/8b/Vector_Icon.png",
        "Item_Weapon_Uzi_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/2/20/Micro_UZI_Icon.png",
        "Item_Weapon_ShotGun_Saiga12_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/5/5a/S12K_Icon.png",
        "Item_Weapon_ShotGun_Berreta686_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/2/20/S686_Icon.png",
        "Item_Weapon_ShotGun_Winchester_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/9/95/S1897_Icon.png",
        "Item_Weapon_SmokeBomb_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/2/21/Smoke_Grenade_Icon.png",
        "Item_Weapon_Grenade_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/3/3c/Frag_Grenade_Icon.png",
        "Item_Weapon_Molotov_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/f/f6/Molotov_Cocktail_Icon.png",
        "Item_Weapon_Pan_C": "https://static.wikia.nocookie.net/pubg_gamepedia/images/e/e6/Pan_Icon.png"
    }
    return weapons.get(weapon_id, "https://wstatic-prod.pubg.com/web/live/static/images/bg-main-kv.jpg")

def _extract_stats(data: dict) -> dict:
    """Helper to extract relevant stats from a mode dictionary"""
    rounds = data.get("roundsPlayed", 0)
    wins = data.get("wins", 0)
    losses = data.get("losses", 0)
    kills = data.get("kills", 0)
    damage = data.get("damageDealt", 0)
    
    return {
        "matches": rounds,
        "wins": wins,
        "top10s": data.get("top10s", 0),
        "kills": kills,
        "assists": data.get("assists", 0),
        "dbnos": data.get("dBNOs", 0), # Knocked
        "headshot_kills": data.get("headshotKills", 0),
        "longest_kill": f"{data.get('longestKill', 0):.1f}m",
        "damage": f"{damage:.0f}",
        "avg_damage": f"{(damage / rounds):.1f}" if rounds > 0 else "0",
        "kd": f"{(kills / losses):.2f}" if losses > 0 else str(kills),
        "win_rate": f"{(wins / rounds * 100):.1f}%" if rounds > 0 else "0%",
        "heals": data.get("heals", 0),
        "revives": data.get("revives", 0)
    }

async def get_pubg_stats(username: str, platform: str = "steam", force_refresh: bool = False) -> Optional[Dict]:
    """
    Fetches PUBG stats using the official PUBG API with caching.
    Returns a structured dict with 'overview', 'fpp', and 'tpp' keys.
    """
    platform = platform.lower()
    cache_key = f"{username}:{platform}"
    current_time = time.time()
    
    # Check Cache
    if not force_refresh and cache_key in _PUBG_CACHE:
        timestamp, cached_data = _PUBG_CACHE[cache_key]
        if current_time - timestamp < CACHE_TTL:
            print(f"⚡ [PUBG] Serving {username} from cache")
            return cached_data
        else:
            print(f"⌛ [PUBG] Cache expired for {username}")
            del _PUBG_CACHE[cache_key]

    api_key = os.getenv("PUBG_API_KEY")
    if not api_key:
        print("❌ PUBG_API_KEY not found in .env")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/vnd.api+json"
    }
    
    base_url = f"https://api.pubg.com/shards/{platform}"

    print(f"🌐 [PUBG] Fetching API for {username}...")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Get Player ID
            player_url = f"{base_url}/players?filter[playerNames]={username}"
            resp = await client.get(player_url, headers=headers)
            
            if resp.status_code != 200:
                print(f"❌ Failed to get player: {resp.status_code} {resp.text}")
                return None
                
            player_data = resp.json()
            if not player_data.get("data"):
                return None
                
            player_id = player_data["data"][0]["id"]
            
            # 2. Get Season Stats
            seasons_url = f"{base_url}/seasons"
            resp_seasons = await client.get(seasons_url, headers=headers)
            if resp_seasons.status_code == 200:
                seasons = resp_seasons.json()["data"]
                current_season = next((s for s in seasons if s["attributes"]["isCurrentSeason"]), None)
                season_id = current_season["id"] if current_season else seasons[-1]["id"]
                
                stats_url = f"{base_url}/players/{player_id}/seasons/{season_id}"
                resp_stats = await client.get(stats_url, headers=headers)
                
                if resp_stats.status_code == 200:
                    stats_data = resp_stats.json()["data"]["attributes"]["gameModeStats"]
                    
                    # Parse Modes
                    fpp_stats = {
                        "solo": _extract_stats(stats_data.get("solo-fpp", {})),
                        "duo": _extract_stats(stats_data.get("duo-fpp", {})),
                        "squad": _extract_stats(stats_data.get("squad-fpp", {}))
                    }
                    
                    tpp_stats = {
                        "solo": _extract_stats(stats_data.get("solo", {})),
                        "duo": _extract_stats(stats_data.get("duo", {})),
                        "squad": _extract_stats(stats_data.get("squad", {}))
                    }
                    
                    # Determine Best Mode for Overview
                    best_mode = "squad-fpp"
                    max_matches = 0
                    for mode, data in stats_data.items():
                        if data["roundsPlayed"] > max_matches:
                            max_matches = data["roundsPlayed"]
                            best_mode = mode
                    
                    overview_stats = _extract_stats(stats_data.get(best_mode, {}))
                    overview_stats["mode_name"] = best_mode
                    
                    result = {
                        "username": username,
                        "platform": platform,
                        "rank": "N/A", # API doesn't provide rank easily
                        "overview": overview_stats,
                        "fpp": fpp_stats,
                        "tpp": tpp_stats
                    }
                    
                    # Save to Cache
                    _PUBG_CACHE[cache_key] = (current_time, result)
                    return result

            return None

        except Exception as e:
            print(f"❌ Error fetching PUBG stats: {e}")
            return None

def _get_map_name(map_code: str) -> str:
    """Maps internal map names to display names"""
    maps = {
        "Desert_Main": "Miramar",
        "DihorOtok_Main": "Vikendi",
        "Erangel_Main": "Erangel",
        "Baltic_Main": "Erangel",
        "Range_Main": "Camp Jackal",
        "Savage_Main": "Sanhok",
        "Summerland_Main": "Karakin",
        "Chimera_Main": "Paramo",
        "Heaven_Main": "Haven",
        "Tiger_Main": "Taego",
        "Kiki_Main": "Deston",
        "Neon_Main": "Rondo"
    }
    return maps.get(map_code, map_code)

def _get_map_image(map_code: str) -> str:
    """Maps internal map names to image URLs"""
    # Using generic placeholders or specific URLs if available. 
    # For now, using a generic PUBG map image or specific ones if known.
    base_url = "https://wstatic-prod.pubg.com/web/live/static/images/maps"
    # These URLs might need verification, using a safe fallback.
    maps = {
        "Desert_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/3a8758f.webp", # Miramar
        "DihorOtok_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/e2b1935.webp", # Vikendi
        "Erangel_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/911fbc0.webp", # Erangel
        "Baltic_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/911fbc0.webp", # Erangel (Remastered)
        "Savage_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/0b79089.webp", # Sanhok
        "Summerland_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/832c04c.webp", # Karakin
        "Tiger_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/1bff1f2.webp", # Taego
        "Kiki_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/8912b02.webp", # Deston
        "Neon_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/57e175a.webp", # Rondo
        "Chimera_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/5582595.webp", # Paramo
        "Heaven_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/5582595.webp", # Haven (Using Paramo as placeholder if not found, or keep generic)
        "Range_Main": "https://wstatic-prod.pubg.com/web/live/main_6b7e058/img/0b79089.webp" # Camp Jackal (Training)
    }
    return maps.get(map_code, "https://wstatic-prod.pubg.com/web/live/static/images/bg-main-kv.jpg")

async def get_last_match(username: str, platform: str = "steam") -> Optional[Dict]:
    """
    Fetches the last match details for a player.
    """
    platform = platform.lower()
    api_key = os.getenv("PUBG_API_KEY")
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/vnd.api+json"
    }
    base_url = f"https://api.pubg.com/shards/{platform}"

    async with httpx.AsyncClient() as client:
        try:
            # 1. Get Player to find last match ID
            player_url = f"{base_url}/players?filter[playerNames]={username}"
            resp = await client.get(player_url, headers=headers)
            
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            player_data = data["data"][0]
            player_id = player_data["id"]
            matches = player_data["relationships"]["matches"]["data"]
            
            if not matches:
                return {"error": "No matches found"}
                
            last_match_id = matches[0]["id"]
            
            # 2. Get Match Details
            match_url = f"{base_url}/matches/{last_match_id}"
            resp_match = await client.get(match_url, headers=headers)
            
            if resp_match.status_code != 200:
                return None
                
            match_data = resp_match.json()
            attributes = match_data["data"]["attributes"]
            included = match_data["included"]
            
            # 3. Parse Match Data
            map_code = attributes["mapName"]
            duration = attributes["duration"]
            game_mode = attributes["gameMode"]
            created_at = attributes["createdAt"]
            
            # Find Participant (Self) and Roster
            my_participant = None
            my_roster = None
            teammates = []
            
            # Map participant IDs to objects for easy lookup
            participants_map = {p["id"]: p for p in included if p["type"] == "participant"}
            
            # Find my participant ID first (we don't have it directly, we have player ID)
            # Actually, participant object has 'attributes.stats.playerId'
            
            for p in included:
                if p["type"] == "participant":
                    stats = p["attributes"]["stats"]
                    if stats["playerId"] == player_id:
                        my_participant = p
                        break
            
            if not my_participant:
                return None
                
            # Find my roster
            my_participant_id = my_participant["id"]
            for p in included:
                if p["type"] == "roster":
                    # Check if my participant ID is in this roster
                    roster_participants = [rp["id"] for rp in p["relationships"]["participants"]["data"]]
                    if my_participant_id in roster_participants:
                        my_roster = p
                        # Get teammates
                        for rp_id in roster_participants:
                            if rp_id != my_participant_id:
                                teammate_p = participants_map.get(rp_id)
                                if teammate_p:
                                    teammates.append(teammate_p["attributes"]["stats"])
                        break
            
            my_stats = my_participant["attributes"]["stats"]
            roster_stats = my_roster["attributes"]["stats"] if my_roster else {}
            
            return {
                "username": username,
                "platform": platform,
                "map_name": _get_map_name(map_code),
                "map_image": _get_map_image(map_code),
                "duration": f"{duration // 60}m {duration % 60}s",
                "mode": game_mode,
                "date": created_at[:10],
                "rank": roster_stats.get("rank", "N/A"),
                "stats": {
                    "kills": my_stats["kills"],
                    "damage": int(my_stats["damageDealt"]),
                    "assists": my_stats["assists"],
                    "dbnos": my_stats["DBNOs"],
                    "distance": f"{(my_stats['walkDistance'] + my_stats['rideDistance']):.1f}m",
                    "time_survived": f"{my_stats['timeSurvived'] // 60}m",
                    "win_place": my_stats["winPlace"]
                },
                "teammates": teammates
            }

        except Exception as e:
            print(f"❌ Error fetching match: {e}")
            return None

# Maintenance update
