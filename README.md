# Don Polo Bot 🤖

**Don Polo Bot** is a feature-rich, multi-purpose Discord bot built with `discord.py`. It combines music playback, game statistics (PUBG & Valorant), moderation tools, and fun mini-games into a single powerful package.

## ✨ Features

### 🎮 Game Stats
- **PUBG**:
  - `/pubg [username] [platform]`: View detailed player stats (Overview, FPP, TPP) with a beautiful interactive UI.
  - `/pubg_match [username]`: Get details about the last match played, including map, rank, damage, and teammates.
  - *Powered by Official PUBG API*.
- **Valorant**:
  - `/valorant [username]`: View player rank, level, and card (Mock/Real API support).

### 🎵 Music System
- High-quality music playback from **YouTube** and **Spotify**.
- Commands: `/play`, `/skip`, `/queue`, `/lyrics`, `/nowplaying`, `/volume`, `/effect` (Bassboost, etc.).
- *Requires FFmpeg*.

### 🛡️ Moderation
- Essential tools to manage your server:
  - `/kick`, `/ban`, `/mute`, `/unmute`, `/warn`.
  - `/purge`: Bulk delete messages.
  - `/poll`: Create voting polls.

### 🎲 Fun & Mini-games
- **Economy & Gambling**: `/slot`, `/coinflip`, `/dadu` (Dice).
- **Games**: `/rps` (Rock Paper Scissors), `/guessnumber`.
- **Utilities**: `/avatar`, `/userinfo`, `/serverinfo`, `/ping`.

### 🎣 Fishing System (New!)
- **Core Gameplay**:
  - `/fish catch`: Catch fish with varying rarities (Common to Legendary). Now features **visuals** for every fish!
  - `/fish inventory`: View your catch history and total value.
  - `/fish shop`: Buy upgraded rods to catch heavier and rarer fish.
  - `/fish trade`: Trade fish with other players.
  - `/fishing_rod`: Equip your purchased rods (e.g., **Dyto Rod**).
- **Competitive**:
  - `/fish leaderboard`: View global rankings for:
    - **Top Fisher** (Most catches)
    - **Heaviest Fish**
    - **Highest Networth**
  - `/fish catalog`: Browse the complete collection of fish by rarity.

### 💻 Modern UI
- Utilizes **Discord Components V2** (Containers) for a clean, app-like experience.
- Interactive buttons and menus for navigation.

---

## 🛠️ Installation

### Prerequisites
- [Python 3.8+](https://www.python.org/downloads/)
- [FFmpeg](https://ffmpeg.org/download.html) (Required for Music) installed and added to PATH.

### Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/don-polo-bot.git
    cd don-polo-bot
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**
    Create a `.env` file in the root directory and add your API keys:
    ```env
    # Discord Bot Token
    DISCORD_TOKEN=your_discord_bot_token

    # Music APIs
    SPOTIFY_CLIENT_ID=your_spotify_client_id
    SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
    GENIUS_TOKEN=your_genius_lyrics_token

    # Game APIs
    PUBG_API_KEY=your_pubg_api_key
    RIOT_API_KEY=your_riot_api_key
    ```

4.  **Run the Bot**
    ```bash
    python main.py
    ```

---

## 📂 Project Structure

- `main.py`: Entry point of the bot.
- `cogs/`: Contains all bot modules (Music, PUBG, Valorant, Help, etc.).
- `utils/`: Helper functions and API wrappers (`pubg_api.py`, `riot_api.py`).
- `.env`: Configuration file (not committed).

## 🤝 Contributing

Feel free to open issues or submit pull requests to improve the bot!

## 📝 License

This project is open-source.

## 🔄 Update Notes
### Latest Updates (Dec 3, 2025)
- **Fishing Update**:
  - Added "Top Fisher" Leaderboard.
  - Added images for all fish in `/fish catch`.
  - Restored `/fish shop` and `/fish trade` commands.
  - Added "Dyto Rod" (Divine Tier).
  - Fixed syntax errors and improved UI.
- **Rod Enhancement (Dec 4, 2025)**:
  - **Rod Leveling**: Upgrade your rods up to Level 10 for massive boosts!
  - **Forge System**: Use `/fish forge` to upgrade rods using materials.
  - **Materials**: Collect "Scrap Metal" and "Magic Pearl" from fishing and salvaging.
  - **Salvage**: Convert unwanted fish into crafting materials with `/fish salvage`.
- **Economy Balancing (Dec 5, 2025)**:
  - **Slot Machine**: Adjusted RTP to ~79% to prevent infinite money glitches.
    
    | Condition | Old Payout | New Payout |
    | :--- | :--- | :--- |
    | 3x 💎 | 10x | **20x** |
    | 3x ⭐ | 7x | **15x** |
    | 2x Match | 2x (Profit 1x) | **1.5x** (Profit 0.5x) |

  - **Fishing Economy**: Rebalanced rod stats for sustainable progression.
    
    | Rod (Max Level +10) | Old Weight Boost | **New Weight Boost** | Old Rarity Boost | **New Rarity Boost** | Est. Income/Catch |
    | :--- | :--- | :--- | :--- | :--- | :--- |
    | **Common** | 2.0x | **1.5x** | +0 | **+0** | ~35 coins |
    | **Masterwork**| 3.0x | **2.5x** | +17 | **+4** | ~1,500 coins |
    | **Dyto** | 6.0x | **3.5x** | +30 | **+8** | ~5,000 coins |

    - **Megalodon Price**: A maxed Dyto Rod can sell a Megalodon for **~125,000 coins**.

- **Music System Overhaul (Dec 5, 2025)**:
  - **Autoplay**: Added `/autoplay` command. The bot now automatically plays related songs when the queue ends.
  - **Playlist Improvements**:
    - **Unlimited Playlists**: Removed the 20-song limit for YouTube and 100-song limit for Spotify.
    - **Lazy Loading**: Songs are now resolved instantly, preventing timeouts when adding large playlists.
    - **Smart Duration**: Fixed "LIVE" duration bug for Spotify tracks by implementing a smart fallback fetch.
    - **Stability**: Improved error handling to skip deleted/unavailable videos automatically.
