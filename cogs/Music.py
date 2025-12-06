import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os
import json
import time
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Optional, List, Dict, Any
import re
import lyricsgenius

# ==============================
# KELAS MUSIC PLAYER (FIXED QUEUE SYSTEM)
# ==============================
class MusicPlayer:
    """Kelas untuk mengelola state musik per-server (guild)."""
    def __init__(self):
        self.queue: List[Dict] = []
        self.current: Optional[Dict] = None
        self.volume: float = 0.5
        self.loop: bool = False
        self.loop_queue: bool = False
        self.autoplay: bool = False
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.effects: Dict[str, str] = {
            "Normal": "",
            "Bass Boost": "bass=g=15",
            "Nightcore": "asetrate=48000*1.25,aresample=48000,atempo=1.25",
            "8D Audio": "apulsator=hz=0.125",
            "Vaporwave": "asetrate=48000*0.8,aresample=48000,atempo=0.8"
        }
        self.current_effect: str = "Normal"
        self.start_time: Optional[float] = None
        self.paused_duration: float = 0
        self.pause_start: Optional[float] = None
        self.disconnect_task: Optional[asyncio.Task] = None
        self.voice_client: Optional[discord.VoiceClient] = None

    def get_current_position(self) -> float:
        if not self.current or not self.start_time: 
            return 0
        current_time = time.time()
        if self.pause_start: 
            return self.pause_start - self.start_time - self.paused_duration
        return current_time - self.start_time - self.paused_duration

    def add_to_queue(self, song: Dict) -> int:
        """FIXED: Add song to queue with proper logging"""
        print(f"📥 Adding to queue: {song.get('title', 'Unknown')[:50]} - Queue length before: {len(self.queue)}")
        self.queue.append(song)
        if self.disconnect_task and not self.disconnect_task.done():
            self.disconnect_task.cancel()
            self.disconnect_task = None
        print(f"📦 Queue length after: {len(self.queue)}")
        return len(self.queue)

    def get_next_song(self) -> Optional[Dict]:
        """FIXED: Improved next song logic"""
        print(f"🔍 Getting next song - Loop: {self.loop}, Loop Queue: {self.loop_queue}, Queue length: {len(self.queue)}")
        
        # Jika loop song aktif, kembalikan lagu yang sama
        if self.loop and self.current:
            print("🔂 Looping current song")
            return self.current.copy()
        
        # Jika loop queue aktif dan ada lagu saat ini
        if self.loop_queue and self.current:
            print("🔁 Looping queue - adding current song back to queue")
            # Tambahkan lagu saat ini ke akhir queue sebelum mengambil lagu berikutnya
            self.queue.append(self.current.copy())
        
        # Jika ada queue, ambil lagu berikutnya
        if self.queue:
            next_song = self.queue.pop(0)
            print(f"⏭️ Next song from queue: {next_song.get('title', 'Unknown')[:50]}")
            return next_song
        
        print("📭 No songs in queue")
        return None

# ==============================
# ENHANCED DISCORD VIEWS
# ==============================
class BaseView(discord.ui.View):
    def __init__(self, music_cog, guild_id: int, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.music_cog = music_cog
        self.guild_id = guild_id
    
    def get_player(self) -> MusicPlayer: 
        return self.music_cog.get_player(self.guild_id)
    
    def get_voice_client(self, guild: discord.Guild) -> Optional[discord.VoiceClient]: 
        return discord.utils.get(self.music_cog.bot.voice_clients, guild=guild)

class EnhancedMusicControlView(BaseView):
    """Enhanced control panel dengan UI yang lebih modern dan responsif"""
    
    def create_enhanced_progress_bar(self, current_pos: float, total_duration: float) -> str:
        """Progress bar yang cantik dan informatif untuk bot musik"""
        if not total_duration or total_duration <= 0:
            return "🔴 **LIVE** ━━━━━━━━━━━━━━━"

        progress = min(current_pos / total_duration, 1.0)
        bar_length = 10
        filled_length = int(progress * bar_length)

        filled_symbol = "▬"
        indicator_symbol = "🔘"
        empty_symbol = "▬"

        if progress >= 1.0:
            bar = filled_symbol * bar_length
        else:
            bar = filled_symbol * filled_length + indicator_symbol + empty_symbol * (bar_length - filled_length - 1)

        current_time = self.music_cog.format_duration(current_pos)
        total_time = self.music_cog.format_duration(total_duration)
        percentage = int(progress * 100)

        return f"`{current_time}` {bar} `{total_time}` **({percentage}%)**"

    def get_status_indicators(self, player: MusicPlayer) -> str:
        """Status indicators dengan emoji yang lebih menarik"""
        indicators = []
        
        if player.loop:
            indicators.append("🔂 **Repeat Song**")
        elif player.loop_queue:
            indicators.append("🔁 **Repeat Queue**")
        else:
            indicators.append("▶️ **Normal Play**")
            
        if player.autoplay:
            indicators.append("♾️ **Autoplay ON**")
            
        volume_bar = "🔊" if player.volume > 0.7 else "🔉" if player.volume > 0.3 else "🔈"
        indicators.append(f"{volume_bar} **{int(player.volume * 100)}%**")
        effect_emoji = {
            "Normal": "🎵",
            "Bass Boost": "🎺",
            "Nightcore": "⚡",
            "8D Audio": "🌀",
            "Vaporwave": "🌊"
        }
        indicators.append(f"{effect_emoji.get(player.current_effect, '🎵')} **{player.current_effect}**")
        
        return " • ".join(indicators)

    def get_enhanced_embed(self) -> discord.Embed:
        """Embed yang lebih modern dan informatif"""
        player = self.get_player()
        
        if not player.current:
            embed = discord.Embed(
                title="🎵 Music Player",
                description="```yaml\nNo music is currently playing\nUse /play to start your musical journey!```",
                color=0x2F3136
            )
            embed.set_footer(text="Ready to play your favorite songs!")
            return embed
        
        song = player.current
        
        colors = [0xFF6B6B, 0x4ECDC4, 0x45B7D1, 0x96CEB4, 0xFECA57, 0xFF9FF3]
        color = random.choice(colors)
        
        embed = discord.Embed(color=color)
        
        title_text = song.get('title', 'Unknown Track')
        if len(title_text) > 60:
            title_text = title_text[:57] + "..."
        
        embed.add_field(
            name="🎤 **Currently Playing**",
            value=f"**[{title_text}]({song.get('webpage_url', '#')})**",
            inline=False
        )
        
        artist = song.get('uploader', 'Unknown Artist')
        requester = song['requester']
        embed.add_field(
            name="**Artist**",
            value=f"```{artist}```",
            inline=True
        )
        embed.add_field(
            name="**Requested by**",
            value=f"```{requester.display_name}```",
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        embed.add_field(
            name="⚙️ **Settings**",
            value=self.get_status_indicators(player),
            inline=False
        )
        
        if player.queue:
            next_songs = []
            for i, song in enumerate(player.queue[:3]):
                next_title = song.get('title', 'Unknown')
                if len(next_title) > 30:
                    next_title = next_title[:27] + "..."
                next_songs.append(f"`{i+1}.` **{next_title}**")
            
            queue_text = "\n".join(next_songs)
            if len(player.queue) > 3:
                queue_text += f"\n`...` **+{len(player.queue) - 3} more songs**"
                
            embed.add_field(
                name=f"📋 **Queue** ({len(player.queue)} songs)",
                value=queue_text,
                inline=False
            )
        
        embed.add_field(
            name=" **Durasi**",
            value=self.create_enhanced_progress_bar(
                player.get_current_position(),
                song.get('duration', 0)
            ),
            inline=False
        )

        if song.get('thumbnail'):
            embed.set_thumbnail(url=song['thumbnail'])
            
        embed.set_footer(
            text=f"Playing since • {time.strftime('%H:%M:%S')}",
            icon_url=requester.display_avatar.url
        )
        
        return embed

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.success, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.get_voice_client(interaction.guild)
        player = self.get_player()
        
        response_text = "" # Teks untuk pesan followup
        
        if vc and vc.is_playing():
            vc.pause()
            player.is_paused = True
            player.pause_start = time.time()
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.primary
            response_text = "⏸️ **Music paused**"
        elif vc and vc.is_paused():
            vc.resume()
            player.is_paused = False
            player.paused_duration += time.time() - (player.pause_start or time.time())
            player.pause_start = None
            button.emoji = "⏸️"
            button.style = discord.ButtonStyle.success
            response_text = "▶️ **Music resumed**"
        else:
            await interaction.response.send_message("❌ **No music is playing**", ephemeral=True)
            return
        
        # --- PERBAIKANNYA ---
        # 1. Respon utama adalah meng-edit panelnya
        await interaction.response.edit_message(embed=self.get_enhanced_embed(), view=self)
        # 2. Kirim pesan ephemeral sebagai followup
        await interaction.followup.send(response_text, ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.get_voice_client(interaction.guild)
        player = self.get_player()
        
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            player.is_playing = False
            player.is_paused = False
            await interaction.response.send_message("⏭️ **Skipped to next song**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ **No music is playing**", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.get_voice_client(interaction.guild)
        player = self.get_player()
        
        if vc:
            player.queue.clear()
            if vc.is_playing() or vc.is_paused():
                vc.stop()
            player.current = None
            player.is_playing = False
            player.is_paused = False
            
            # --- PERBAIKANNYA ---
            await interaction.response.edit_message(embed=self.get_enhanced_embed(), view=self)
            await interaction.followup.send("⏹️ **Music stopped and queue cleared**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ **Not connected to voice**", ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=0)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.get_player()
        if len(player.queue) < 2:
            await interaction.response.send_message("❌ **Need at least 2 songs to shuffle**", ephemeral=True)
            return
        
        random.shuffle(player.queue)
        await interaction.response.send_message(f"🔀 **Queue shuffled** ({len(player.queue)} songs)", ephemeral=True)

    @discord.ui.button(emoji="🔂", style=discord.ButtonStyle.secondary, row=1)
    async def loop_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.get_player()
        player.loop = not player.loop
        if player.loop:
            player.loop_queue = False
            button.style = discord.ButtonStyle.success
        else:
            button.style = discord.ButtonStyle.secondary
            
        response_text = f"🔂 **Loop Song: {'ON' if player.loop else 'OFF'}**"
        
        # --- PERBAIKANNYA ---
        await interaction.response.edit_message(embed=self.get_enhanced_embed(), view=self)
        await interaction.followup.send(response_text, ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=1)
    async def loop_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.get_player()
        player.loop_queue = not player.loop_queue
        if player.loop_queue:
            player.loop = False
            button.style = discord.ButtonStyle.success
        else:
            button.style = discord.ButtonStyle.secondary
            
        response_text = f"🔁 **Loop Queue: {'ON' if player.loop_queue else 'OFF'}**"
        
        # --- PERBAIKANNYA ---
        await interaction.response.edit_message(embed=self.get_enhanced_embed(), view=self)
        await interaction.followup.send(response_text, ephemeral=True)

class VolumeModal(discord.ui.Modal, title='🔊 Adjust Volume'):
    def __init__(self, music_cog, guild_id: int):
        super().__init__()
        self.music_cog = music_cog
        self.guild_id = guild_id

    volume = discord.ui.TextInput(
        label='Volume Level (0-150)',
        placeholder='Enter volume level...',
        default='50',
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            level = int(self.volume.value)
            if not 0 <= level <= 150:
                raise ValueError("Volume must be between 0-150")
                
            player = self.music_cog.get_player(self.guild_id)
            player.volume = level / 100
            
            vc = discord.utils.get(self.music_cog.bot.voice_clients, guild=interaction.guild)
            if vc and hasattr(vc.source, 'volume'):
                vc.source.volume = level / 100
                
            volume_emoji = "🔊" if level > 70 else "🔉" if level > 30 else "🔈"
            await interaction.response.send_message(
                f"{volume_emoji} **Volume set to {level}%**", 
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ **Invalid volume level! Use 0-150**", 
                ephemeral=True
            )

class EffectsSelect(discord.ui.Select):
    def __init__(self, music_cog, guild_id: int):
        self.music_cog = music_cog
        self.guild_id = guild_id
        
        options = [
            discord.SelectOption(label="Normal", description="No audio effects", emoji="🎵"),
            discord.SelectOption(label="Bass Boost", description="Enhanced bass frequencies", emoji="🎺"),
            discord.SelectOption(label="Nightcore", description="Higher pitch and faster tempo", emoji="⚡"),
            discord.SelectOption(label="8D Audio", description="Surround sound effect", emoji="🌀"),
            discord.SelectOption(label="Vaporwave", description="Slowed and pitched down", emoji="🌊")
        ]
        
        super().__init__(placeholder="🎧 Choose audio effect...", options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        player = self.music_cog.get_player(self.guild_id)
        player.current_effect = self.values[0]
        
        effect_descriptions = {
            "Normal": "Clear audio without effects",
            "Bass Boost": "Enhanced low frequencies",
            "Nightcore": "High energy, fast-paced audio",
            "8D Audio": "Immersive spatial audio experience",
            "Vaporwave": "Chill, retro aesthetic sound"
        }
        
        await interaction.response.send_message(
            f"🎧 **Effect changed to {self.values[0]}**\n"
            f"*{effect_descriptions.get(self.values[0], '')}*\n"
            f"**Note:** Effect will apply to the next song or when replaying current song.",
            ephemeral=True
        )

class EnhancedControlPanel(BaseView):
    """Panel kontrol utama yang lebih canggih"""
    
    def __init__(self, music_cog, guild_id: int):
        super().__init__(music_cog, guild_id, timeout=600)
        self.add_item(EffectsSelect(music_cog, guild_id))

    @discord.ui.button(label="🔊 Volume", style=discord.ButtonStyle.secondary, row=1)
    async def volume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = VolumeModal(self.music_cog, self.guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 Queue", style=discord.ButtonStyle.secondary, row=1)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # === INI ADALAH KUNCINYA ===
            # Pastikan 'ephemeral=True' ada di sini.
            # Ini memberi tahu Discord bahwa SELURUH interaksi ini bersifat pribadi.
            await interaction.response.defer(ephemeral=True) 
            
            player = self.get_player()
            
            print("QUEUE_BUTTON: Defer berhasil. Menghitung durasi...")
            total_duration = await self.music_cog.calculate_total_duration(player.queue)
            print(f"QUEUE_BUTTON: Durasi dihitung: {total_duration}")

            view = QueuePaginatorView(player.queue, player.current, self.music_cog, total_duration)
            initial_embed = view.create_queue_embed(total_duration)
            print("QUEUE_BUTTON: Embed dibuat. Mengirim followup...")
            
            # followup.send() akan OTOMATIS menjadi pribadi
            # karena 'defer()' di atas sudah ephemeral.
            await interaction.followup.send(
                embed=initial_embed, 
                view=view
            )
            print("QUEUE_BUTTON: Followup terkirim.")
            
        except Exception as e:
            print(f"!!!!!!!!!! ERROR PADA queue_button !!!!!!!!!!!")
            import traceback
            traceback.print_exc()
            try:
                # Pesan error ini juga akan otomatis ephemeral
                await interaction.followup.send(
                    f"❌ Terjadi error internal saat mengambil antrean: `{e}`", 
                    ephemeral=True
                )
            except:
                pass

    @discord.ui.button(label="🎤 Lirik", style=discord.ButtonStyle.secondary, row=1)
    async def lyrics_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        player = self.get_player()
        if not player.current:
            return await interaction.followup.send("❌ **Tidak ada lagu yang sedang diputar.**", ephemeral=True)

        raw_title = player.current.get('title', '')
        cleaned_title = self.music_cog.clean_title_for_lyrics(raw_title)
        original_artist = player.current.get('uploader', '')
        search_query = f"{cleaned_title} {original_artist}"
        
        await self.music_cog.fetch_and_send_lyrics(interaction, search_query, original_artist, cleaned_title)

class QueuePaginatorView(discord.ui.View):
    """View interaktif untuk menampilkan antrean dengan paginasi (halaman)."""
    
    def __init__(self, queue: List[Dict], current: Optional[Dict], music_cog: 'Music', total_duration: int):
        super().__init__(timeout=180.0)  # Timeout 3 menit
        self.queue = list(queue)  # Buat salinan queue
        self.current = current
        self.music_cog = music_cog
        self.total_duration_value = total_duration  # <-- TAMBAHKAN INI (untuk disimpan)
        self.current_page = 0
        self.items_per_page = 10
        self.total_pages = max(1, (len(self.queue) + self.items_per_page - 1) // self.items_per_page)

    def create_queue_embed(self, total_duration: int) -> discord.Embed:
        """Membuat embed untuk halaman saat ini. (FIXED FOR 1024 CHAR LIMIT)"""
        
        # 1. Update status tombol
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
        
        # 2. Bangun teks deskripsi antrean (queue_description)
        queue_description = ""
        if not self.queue:
            queue_description = "*Antrean kosong*"
        else:
            start_index = self.current_page * self.items_per_page
            end_index = start_index + self.items_per_page
            page_items = self.queue[start_index:end_index]
            
            for i, song in enumerate(page_items, start=start_index + 1):
                title = song.get('title', 'Unknown')
                if len(title) > 45:
                    title = title[:42] + "..."
                
                duration = self.music_cog.format_duration(song.get('duration'))
                
                # Format baris
                line = (
                    f"`{i:2d}.` **[{title}]({song.get('webpage_url')})**\n"
                    f"     `{duration}` | {song['requester'].mention}\n"
                )
                
                # Pengecekan keamanan agar tidak melebihi batas deskripsi (4096)
                if len(queue_description) + len(line) > 4000:
                    queue_description += "\n*... dan lebih banyak lagu di halaman ini (terpotong)*"
                    break
                
                queue_description += line
        
        # 3. Buat embed, masukkan daftar antrean ke 'description'
        embed = discord.Embed(
            title=f"Music Queue - Halaman {self.current_page + 1}/{self.total_pages}",
            color=0x96CEB4,
            description=queue_description  # <-- INI PERUBAHAN UTAMANYA
        )
        
        # 4. Tambahkan 'Now Playing' sebagai field terpisah (ini aman)
        if self.current:
            current_title = self.current.get('title', 'Unknown')
            if len(current_title) > 60:
                current_title = current_title[:57] + "..."
            embed.add_field(
                name="🎵 **Now Playing**",
                value=f"**[{current_title}]({self.current.get('webpage_url')})**\n"
                      f"Requested by: {self.current['requester'].mention}",
                inline=False
            )
        else:
            embed.add_field(name="🎵 **Now Playing**", value="*Tidak ada lagu diputar*", inline=False)
        
        # 5. Tambahkan footer
        footer_text = (
            f"Total Lagu: {len(self.queue)} • "
            f"Total Durasi: {self.music_cog.format_duration(total_duration)}"
        )
        embed.set_footer(text=footer_text)
        
        return embed

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        
        embed = self.create_queue_embed(self.total_duration_value)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        
        embed = self.create_queue_embed(self.total_duration_value)
        await interaction.response.edit_message(embed=embed, view=self)

class SearchSelect(discord.ui.Select):
    def __init__(self, results: List[Dict], music_cog, guild_id: int):
        self.results = results
        self.music_cog = music_cog
        self.guild_id = guild_id
        
        options = []
        for i, result in enumerate(results[:5]):
            title = result.get('title', 'Unknown')
            if len(title) > 80:
                title = title[:77] + "..."
                
            uploader = result.get('uploader', 'Unknown')
            if len(uploader) > 30:
                uploader = uploader[:27] + "..."
                
            options.append(discord.SelectOption(
                label=f"{i+1}. {title}",
                value=str(i),
                description=f"{uploader} - {music_cog.format_duration(result.get('duration'))}",
                emoji="🎵"
            ))
        
        super().__init__(placeholder="🎵 Choose a song to play...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.music_cog.handle_song_selection(interaction, self.results[int(self.values[0])])

# ==============================
# COG MUSIK UTAMA (FIXED QUEUE SYSTEM)
# ==============================
class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: Dict[int, MusicPlayer] = {}
        self.spotify = None
        self.genius = None

        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': False,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'extract_flat': False,
            'cookiefile': None,
            'age_limit': None,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 10M',
            'options': '-vn -bufsize 1024k'
        }
        
        self.init_spotify()
        self.init_genius()

    def init_spotify(self):
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

        if client_id and client_secret:
            try:
                self.spotify = spotipy.Spotify(
                    auth_manager=SpotifyClientCredentials(
                        client_id=client_id,
                        client_secret=client_secret
                    )
                )
                print("✅ Spotify client successfully initialized from .env")
            except Exception as e:
                print(f"⚠️ Failed to initialize Spotify: {e}")
        else:
            print("⚠️ Spotify credentials not found in .env (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)")

    def init_genius(self):
        """Initialize Genius client from .env."""
        token = os.getenv('GENIUS_TOKEN')
        
        if token:
            try:
                self.genius = lyricsgenius.Genius(
                    token,
                    remove_section_headers=True,
                    skip_non_songs=True,
                    excluded_terms=["(Remix)", "(Live)"]
                )
                print("✅ Genius client successfully initialized from .env")
            except Exception as e:
                print(f"⚠️ Failed to initialize Genius: {e}")
        else:
            print("⚠️ Genius token not found in .env (GENIUS_TOKEN). Lyrics feature disabled.")

    def get_player(self, guild_id: int) -> MusicPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer()
        return self.players[guild_id]

    def format_duration(self, seconds: Optional[int]) -> str:
        if not seconds:
            return "00:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def clean_title_for_lyrics(self, title: str) -> str:
        """Enhanced title cleaning for better lyrics search"""
        if not title:
            return ""
        
        title = re.sub(r'\b(M/?V|MV|Music Video|Official Video|Official Music Video)\b', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\[.*?\]', '', title)
        title = re.sub(r'\(.*?\)', '', title)
        title = re.sub(r'\b(ft\.?|feat\.?|featuring)\b.*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\b(HD|4K|1080p|720p|480p)\b', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\b(19|20)\d{2}\b', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title

    async def search_youtube(self, query: str, max_results: int = 1) -> List[Dict]:
        opts = self.ytdl_opts.copy()
        if not query.startswith(('http://', 'https://')):
            opts['default_search'] = f'ytsearch{max_results}'
        
        loop = asyncio.get_event_loop()
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await loop.run_in_executor(
                    None, lambda: ydl.extract_info(query, download=False)
                )
            
            if 'entries' in info:
                entries = [e for e in info['entries'] if e]
                print(f"📋 Found {len(entries)} entries")
                return entries
            return [info] if info else []
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []

    async def process_spotify(self, query: str) -> List[str]:
        if not self.spotify:
            return []
        
        try:
            if 'playlist' in query:
                results = self.spotify.playlist_tracks(query)
            else:
                results = self.spotify.album_tracks(query)
            
            all_tracks = []
            while results:
                for t in results['items']:
                    if t.get('track'):
                        track_name = t['track']['name']
                        artist_name = t['track']['artists'][0]['name']
                        all_tracks.append(f"{track_name} {artist_name}")
                
                if results['next']:
                    results = self.spotify.next(results)
                else:
                    results = None
            
            return all_tracks
        except Exception as e:
            print(f"❌ Spotify error: {e}")
            return []

    async def connect_to_voice(self, interaction: discord.Interaction) -> Optional[discord.VoiceClient]:
        if not interaction.user.voice:
            await interaction.followup.send("❌ **You must be in a voice channel!**", ephemeral=True)
            return None
        
        vc = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        channel = interaction.user.voice.channel
        
        try:
            if not vc:
                vc = await channel.connect()
                print(f"🔌 Connected to voice channel: {channel.name}")
            elif vc.channel != channel:
                await vc.move_to(channel)
                print(f"🔀 Moved to voice channel: {channel.name}")
            return vc
        except Exception as e:
            await interaction.followup.send(f"❌ **Connection failed:** {e}", ephemeral=True)
            return None

    async def schedule_disconnect(self, guild_id: int):
        player = self.get_player(guild_id)
        guild = self.bot.get_guild(guild_id)
        
        if player.disconnect_task and not player.disconnect_task.done():
            player.disconnect_task.cancel()

        async def disconnect_after_delay():
            try:
                await asyncio.sleep(300)
                vc = discord.utils.get(self.bot.voice_clients, guild=guild)
                if vc and not player.is_playing and not player.is_paused:
                    await vc.disconnect()
                    if guild_id in self.players:
                        del self.players[guild_id]
            except asyncio.CancelledError:
                pass

        player.disconnect_task = self.bot.loop.create_task(disconnect_after_delay())

    async def play_song(self, vc: discord.VoiceClient, song_info: Dict, guild_id: int):
        """FIXED: Improved song playback system"""
        player = self.get_player(guild_id)
        
        if player.is_playing:
            print(f"⚠️ Already playing, adding to queue instead for guild {guild_id}")
            player.add_to_queue(song_info)
            return
        
        player.is_playing = True
        player.is_paused = False
        
        def after_playing(error):
            coro = self.after_song_callback(error, guild_id)
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"❌ Error in after_playing callback: {e}")

        try:
            # === LAZY LOADING IMPLEMENTATION ===
            # Check if we need to resolve the URL (it might be a partial object from playlist)
            if not song_info.get('url') or not song_info.get('duration'):
                print(f"🔄 Lazy loading song details for: {song_info.get('title', 'Unknown')}")
                
                loop = asyncio.get_event_loop()
                
                # If it's a Spotify search query (just a string in 'webpage_url' or similar)
                # Or if it's a YouTube partial object
                search_query = song_info.get('webpage_url')
                
                # If it was a Spotify search term stored in 'webpage_url'
                if song_info.get('is_spotify_search'):
                     search_query = song_info.get('spotify_query')
                     # We need to search first
                     print(f"🔍 Resolving Spotify query: {search_query}")
                     with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                        try:
                            info = await loop.run_in_executor(
                                None, lambda: ydl.extract_info(f"ytsearch1:{search_query}", download=False)
                            )
                            if 'entries' in info and info['entries']:
                                url_info = info['entries'][0]
                            else:
                                raise Exception("No results found for Spotify query")
                        except Exception as e:
                             print(f"❌ Failed to resolve Spotify query: {e}")
                             raise e
                else:
                    # Standard YouTube lazy load
                    with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                        url_info = await loop.run_in_executor(
                            None, lambda: ydl.extract_info(song_info['webpage_url'], download=False)
                        )

                audio_url = url_info.get('url')
                
                if not audio_url:
                    # Fallback: try different format
                    formats = url_info.get('formats', [])
                    for fmt in formats:
                        if fmt.get('acodec') != 'none' and fmt.get('url'):
                            audio_url = fmt['url']
                            break
                
                if not audio_url:
                    raise Exception("Failed to get audio URL")
                
                # Update song info with fresh data
                song_info['url'] = audio_url
                # Ensure duration is an int to avoid "LIVE" status if it's not actually live
                try:
                    duration_val = url_info.get('duration')
                    
                    # Fallback: If duration is missing or 0, fetch full details from the specific video URL
                    if not duration_val:
                        video_url = url_info.get('webpage_url')
                        if video_url:
                            print(f"🔄 Duration missing ({duration_val}), fetching full video details for: {video_url}")
                            # Use a fresh YTDL instance to ensure we get full info (not flat)
                            fallback_opts = self.ytdl_opts.copy()
                            fallback_opts['extract_flat'] = False
                            with yt_dlp.YoutubeDL(fallback_opts) as ydl_full:
                                full_info = await loop.run_in_executor(
                                    None, lambda: ydl_full.extract_info(video_url, download=False)
                                )
                                if full_info:
                                    duration_val = full_info.get('duration')
                                    # Update other fields to be safe
                                    url_info = full_info
                                    audio_url = full_info.get('url') or audio_url
                                    song_info['url'] = audio_url # Update audio URL if it changed

                    song_info['duration'] = int(duration_val) if duration_val is not None else 0
                except Exception as e:
                    print(f"DEBUG: Failed to parse duration: {e}")
                    song_info['duration'] = 0
                    
                song_info['thumbnail'] = url_info.get('thumbnail')
                song_info['title'] = url_info.get('title', song_info.get('title', 'Unknown'))
                song_info['uploader'] = url_info.get('uploader', song_info.get('uploader', 'Unknown'))
                # CRITICAL FIX: Update webpage_url to the actual YouTube URL
                song_info['webpage_url'] = url_info.get('webpage_url', song_info.get('webpage_url'))
                
                # Update current player state with full info
                player.current = song_info
            
            # Apply audio effects and volume
            opts = self.ffmpeg_options.copy()
            filters = [f"volume={player.volume}"]
            if player.current_effect != "Normal":
                filters.append(player.effects[player.current_effect])
            
            opts['options'] = f"-vn -af \"{','.join(filters)}\""
            
            # Create audio source
            # Ensure audio_url is available from song_info (it should be by now)
            source = discord.FFmpegPCMAudio(song_info['url'], **opts)
            source = discord.PCMVolumeTransformer(source, volume=player.volume)
            
            # Stop any current playback
            if vc.is_playing() or vc.is_paused():
                vc.stop()
                await asyncio.sleep(0.5)
            
            # Start playback
            vc.play(source, after=after_playing)
            
            player.start_time = time.time()
            player.paused_duration = 0
            player.pause_start = None
            
            print(f"✅ Now playing: {song_info.get('title', 'Unknown')[:50]} for guild {guild_id}")
            
        except Exception as e:
            print(f"❌ Failed to play song: {e}")
            player.is_playing = False
            await asyncio.sleep(1)
            # Skip to next song if this one fails
            await self.play_next(guild_id)

    async def after_song_callback(self, error, guild_id: int):
        """FIXED: Improved callback system dengan delay yang tepat"""
        player = self.get_player(guild_id)
        
        if error:
            print(f"❌ Playback error for guild {guild_id}: {error}")
        
        player.is_playing = False
        player.is_paused = False
        
        print(f"🎵 Song finished for guild {guild_id}, preparing next song...")
        
        # Beri waktu untuk cleanup dan memastikan playback benar-benar selesai
        await asyncio.sleep(1)
        
        await self.play_next(guild_id)

    async def get_autoplay_song(self, last_song: Dict) -> Optional[Dict]:
        """Get a related song for autoplay based on the last played song"""
        if not last_song:
            return None
            
        title = last_song.get('title', '')
        artist = last_song.get('uploader', '')
        
        # Clean title for better search
        clean_title = self.clean_title_for_lyrics(title)
        search_query = f"{clean_title} {artist} official audio"
        
        print(f"♾️ Autoplay searching for: {search_query}")
        
        try:
            # Search for 5 results to have options
            results = await self.search_youtube(search_query, max_results=5)
            
            if not results:
                return None
                
            # Filter out the song that just played (by URL or title similarity)
            last_url = last_song.get('webpage_url', '')
            
            for result in results:
                if result.get('webpage_url') != last_url:
                    # Basic check to avoid playing the exact same video
                    return result
            
            # If all else fails, return the first result
            return results[0] if results else None
            
        except Exception as e:
            print(f"❌ Autoplay error: {e}")
            return None

    async def play_next(self, guild_id: int):
        """FIXED: Improved next song handling dengan logging yang lebih baik"""
        player = self.get_player(guild_id)
        guild = self.bot.get_guild(guild_id)
        vc = discord.utils.get(self.bot.voice_clients, guild=guild)
        
        if not vc:
            print(f"⚠️ No voice client for guild {guild_id}")
            player.is_playing = False
            player.is_paused = False
            return
        
        # Tunggu sebentar untuk memastikan playback sebelumnya benar-benar berhenti
        await asyncio.sleep(0.5)
        
        # Cek apakah masih ada playback aktif
        if vc.is_playing():
            print(f"⚠️ Voice client still playing for guild {guild_id}, waiting...")
            await asyncio.sleep(1)
            if vc.is_playing():
                print(f"❌ Voice client still playing, skipping play_next for guild {guild_id}")
                return
        
        next_song = player.get_next_song()
        
        if next_song:
            print(f"⏭️ Playing next song in queue for guild {guild_id}: {next_song.get('title', 'Unknown')[:50]}")
            player.current = next_song
            await self.play_song(vc, next_song, guild_id)
        else:
            # Try Autoplay if queue is empty
            if player.autoplay and player.current:
                print(f"♾️ Queue empty, trying Autoplay for guild {guild_id}")
                autoplay_song = await self.get_autoplay_song(player.current)
                
                if autoplay_song:
                    print(f"♾️ Autoplay found: {autoplay_song.get('title', 'Unknown')}")
                    autoplay_song['requester'] = self.bot.user # Bot is the requester
                    player.current = autoplay_song
                    
                    # Notify about autoplay
                    try:
                        # Try to find a channel to send notification (this is tricky without context, 
                        # but usually we don't spam text channels for every song unless requested.
                        # For now, we just play it.)
                        pass
                    except:
                        pass
                        
                    await self.play_song(vc, autoplay_song, guild_id)
                    return

            print(f"📭 Queue empty for guild {guild_id}")
            player.current = None
            player.is_playing = False
            await self.schedule_disconnect(guild_id)

    async def handle_song_selection(self, interaction: discord.Interaction, song_info: Dict):
        """FIXED: Improved song selection with proper queue handling"""
        vc = await self.connect_to_voice(interaction)
        if not vc:
            return
        
        player = self.get_player(interaction.guild.id)
        song_info['requester'] = interaction.user
        
        print(f"🎯 Handling song selection - Is playing: {player.is_playing}, Has current: {player.current is not None}")
        
        if not player.is_playing and player.current is None:
            # Jika tidak ada yang sedang diputar, mulai putar lagu
            print(f"🎵 Starting playback for new song: {song_info.get('title', 'Unknown')[:50]}")
            player.current = song_info
            await self.play_song(vc, song_info, interaction.guild.id)
            
            embed = self.create_song_embed(song_info, "🎵 Now Playing", 0x00D4AA)
            control_view = EnhancedMusicControlView(self, interaction.guild.id)
            panel_view = EnhancedControlPanel(self, interaction.guild.id)
            
            await interaction.edit_original_response(embed=embed, view=control_view)
            await interaction.followup.send("**🎛️ Enhanced Control Panel**", view=panel_view, ephemeral=True)
        else:
            # Jika sedang ada yang diputar, tambahkan ke queue
            print(f"📥 Adding to queue: {song_info.get('title', 'Unknown')[:50]}")
            pos = player.add_to_queue(song_info)
            embed = self.create_song_embed(song_info, "➕ Added to Queue", 0x4ECDC4)
            embed.add_field(name="📋 Position", value=f"#{pos}", inline=True)
            await interaction.edit_original_response(embed=embed, view=None)

    def create_song_embed(self, song_info: Dict, title: str, color: int) -> discord.Embed:
        embed = discord.Embed(title=title, color=color, url=song_info.get('webpage_url'))
        
        song_title = song_info.get('title', 'Unknown')
        if len(song_title) > 60:
            song_title = song_title[:57] + "..."
        
        embed.add_field(name="🎤 Title", value=f"**{song_title}**", inline=False)
        embed.add_field(name="👤 Artist", value=song_info.get('uploader', 'Unknown'), inline=True)
        embed.add_field(name="⏱️ Duration", value=self.format_duration(song_info.get('duration')), inline=True)
        
        if thumbnail := song_info.get('thumbnail'):
            embed.set_thumbnail(url=thumbnail)
        
        if requester := song_info.get('requester'):
            embed.set_footer(
                text=f"Requested by {requester.display_name}",
                icon_url=requester.display_avatar.url
            )
        
        return embed
    
    async def calculate_total_duration(self, queue: List[Dict]) -> int:
        """
        Menghitung total durasi antrean di thread terpisah agar tidak memblokir.
        """
        if not queue:
            return 0
        
        loop = asyncio.get_event_loop()
        
        def blocking_sum():
            try:
                print("SUM_THREAD: Memulai kalkulasi 'sum'...")
                total_dur = sum(song.get('duration', 0) for song in queue if song.get('duration'))
                print(f"SUM_THREAD: Kalkulasi 'sum' selesai: {total_dur}")
                return total_dur
            except Exception as e:
                print(f"!!!!!!!!!! ERROR DI DALAM THREAD blocking_sum !!!!!!!!!!!")
                import traceback
                traceback.print_exc()
                return 0 # Kembalikan 0 jika gagal
        
        try:
            print("CALC_DURATION: Menjalankan 'sum' di executor...")
            total_duration = await loop.run_in_executor(None, blocking_sum)
            print("CALC_DURATION: Executor selesai.")
            return total_duration
        except Exception as e:
            print(f"!!!!!!!!!! ERROR SAAT MEMANGGIL EXECUTOR !!!!!!!!!!!")
            import traceback
            traceback.print_exc()
            return 0 # Kembalikan 0 jika gagal

    # ==============================
    # SLASH COMMANDS (FIXED)
    # ==============================
    @app_commands.command(name="play", description="🎵 Play music from YouTube, Spotify, or YouTube Playlist")
    @app_commands.describe(query="YouTube/Spotify URL, YouTube Playlist URL, or search query")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        print(f"🎵 Play command received: {query[:100]}")

        # Check for YouTube playlist
        youtube_playlist_patterns = [
            r"(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/(playlist|watch)\?(.*&)?list=([a-zA-Z0-9_-]+)",
            r"(https?:\/\/)?(www\.)?youtube\.com\/playlist\?list=([a-zA-Z0-9_-]+)",
            r"(https?:\/\/)?(www\.)?youtube\.com\/watch\?.*list=([a-zA-Z0-9_-]+)"
        ]
        
        is_youtube_playlist = any(re.search(pattern, query) for pattern in youtube_playlist_patterns)
        
        if is_youtube_playlist:
            vc = await self.connect_to_voice(interaction)
            if not vc:
                return
            
            player = self.get_player(interaction.guild.id)
            
            await interaction.followup.send("🔄 **Processing YouTube playlist...**")
            
            try:
                # Process playlist
                opts = self.ytdl_opts.copy()
                opts['extract_flat'] = True
                
                loop = asyncio.get_event_loop()
                with yt_dlp.YoutubeDL(opts) as ydl:
                    playlist_info = await loop.run_in_executor(
                        None, lambda: ydl.extract_info(query, download=False)
                    )
                
                if not playlist_info or 'entries' not in playlist_info:
                    return await interaction.edit_original_response(
                        content="❌ **Failed to process YouTube playlist.**"
                    )
                
                # REMOVED LIMIT: entries = [e for e in playlist_info['entries'] if e][:20]
                entries = [e for e in playlist_info['entries'] if e]
                
                print(f"📋 Playlist entries found: {len(entries)}")
                
                # Process first song immediately to start playback
                if entries:
                    first_entry = entries[0]
                    video_url = first_entry.get('url') or f"https://www.youtube.com/watch?v={first_entry.get('id', '')}"
                    
                    # We still want to resolve the first song fully to ensure it works
                    # But for speed, we can also lazy load it if we trust the partial info.
                    # Let's resolve it to be safe and give good "Now Playing" info.
                    opts['extract_flat'] = False
                    with yt_dlp.YoutubeDL(opts) as ydl_single:
                        video_info = await loop.run_in_executor(
                            None, lambda: ydl_single.extract_info(video_url, download=False)
                        )
                    
                    if video_info:
                        first_song = {
                            'title': video_info.get('title', first_entry.get('title', 'Unknown')),
                            'uploader': video_info.get('uploader', first_entry.get('uploader', 'Unknown')),
                            'duration': video_info.get('duration', first_entry.get('duration')),
                            'webpage_url': video_info.get('webpage_url', video_url),
                            'thumbnail': video_info.get('thumbnail', first_entry.get('thumbnail')),
                            'url': video_info.get('url'), # Full URL for first song
                            'requester': interaction.user
                        }
                        
                        player.current = first_song
                        await self.play_song(vc, first_song, interaction.guild.id)
                        
                        # Add remaining songs as PARTIAL objects (Lazy Load)
                        added_count = 0
                        for entry in entries[1:]:
                            video_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                            song_data = {
                                'title': entry.get('title', 'Unknown'),
                                'uploader': entry.get('uploader', 'Unknown'),
                                'duration': entry.get('duration'), # Might be None, resolved later
                                'webpage_url': video_url,
                                'thumbnail': entry.get('thumbnail'),
                                'url': None, # Indicates needs resolution
                                'requester': interaction.user
                            }
                            player.add_to_queue(song_data)
                            added_count += 1
                        
                        embed = discord.Embed(
                            title="✅ YouTube Playlist Added",
                            description=f"**{len(entries)}** songs added from playlist.\n"
                                      f"**Now playing:** {first_song.get('title', 'Unknown')}\n"
                                      f"**Queue:** +{added_count} more songs",
                            color=0x00FF00
                        )
                        
                        control_view = EnhancedMusicControlView(self, interaction.guild.id)
                        await interaction.edit_original_response(content=None, embed=embed, view=control_view)
                        
                    else:
                        await interaction.edit_original_response(
                            content="❌ **Failed to process first song from playlist.**"
                        )
                else:
                    await interaction.edit_original_response(
                        content="❌ **No songs found in playlist.**"
                    )
                        
            except Exception as e:
                print(f"❌ Playlist processing error: {e}")
                import traceback
                traceback.print_exc()
                await interaction.edit_original_response(
                    content="❌ **Failed to process YouTube playlist.**"
                )
            return
        
        # Check for Spotify
        spotify_match = re.match(
            r"https?:\/\/open\.spotify\.com\/(?:intl-\w{2,3}\/)?(track|playlist|album)\/([a-zA-Z0-9]+)", 
            query
        )
        
        if spotify_match:
            if not self.spotify:
                return await interaction.followup.send("❌ **Spotify feature not active.**", ephemeral=True)
            
            type_name, spotify_id = spotify_match.groups()
            
            if type_name == 'track':
                track = self.spotify.track(spotify_id)
                search_query = f"{track['name']} {track['artists'][0]['name']}"
                results = await self.search_youtube(search_query)
                
                if not results:
                    return await interaction.followup.send(
                        "❌ **Spotify song not found on YouTube.**", ephemeral=True
                    )
                
                await self.handle_song_selection(interaction, results[0])
            else:
                vc = await self.connect_to_voice(interaction)
                if not vc:
                    return
                
                await interaction.followup.send(f"🔄 **Processing Spotify {type_name}...**")
                tracks = await self.process_spotify(query)
                
                if not tracks:
                    return await interaction.edit_original_response(
                        content=f"❌ **Failed to fetch songs from Spotify {type_name}.**"
                    )
                
                player = self.get_player(interaction.guild.id)
                count = 0
                
                # Process first track immediately
                if tracks:
                    first_track_query = tracks[0]
                    results = await self.search_youtube(first_track_query)
                    if results:
                        song = results[0]
                        song['requester'] = interaction.user
                        
                        if not player.is_playing and not player.current:
                            player.current = song
                            await self.play_song(vc, song, interaction.guild.id)
                        else:
                            player.add_to_queue(song)
                        count += 1
                
                # Add remaining tracks as LAZY queries
                for track_query in tracks[1:]:
                    # Create a "placeholder" song object for Spotify queries
                    song_data = {
                        'title': track_query, # Use query as title temporarily
                        'uploader': 'Spotify',
                        'duration': 0, # Unknown
                        'webpage_url': track_query, # Store query here
                        'spotify_query': track_query,
                        'is_spotify_search': True,
                        'url': None,
                        'requester': interaction.user
                    }
                    player.add_to_queue(song_data)
                    count += 1
                
                embed = discord.Embed(
                    title=f"✅ {type_name.capitalize()} Added",
                    description=f"**{count}** of **{len(tracks)}** songs successfully added.",
                    color=0x1DB954
                )
                
                control_view = EnhancedMusicControlView(self, interaction.guild.id)
                panel_view = EnhancedControlPanel(self, interaction.guild.id)
                
                await interaction.edit_original_response(content=None, embed=embed, view=control_view)
                await interaction.followup.send("**🎛️ Enhanced Control Panel**", view=panel_view, ephemeral=True)
        else:
            # Regular YouTube search
            results = await self.search_youtube(query)
            if not results:
                return await interaction.followup.send("❌ **Song not found.**", ephemeral=True)
            
            await self.handle_song_selection(interaction, results[0])

    @app_commands.command(name="lyrics", description="🎤 Mencari lirik dari lagu yang sedang diputar atau lagu spesifik")
    async def lyrics(self, interaction: discord.Interaction, judul: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        
        search_query = judul
        original_artist = ""
        cleaned_title = ""

        if not search_query:
            player = self.get_player(interaction.guild.id)
            if player.current:
                raw_title = player.current.get('title', '')
                cleaned_title = self.clean_title_for_lyrics(raw_title)
                original_artist = player.current.get('uploader', '')
                search_query = f"{cleaned_title} {original_artist}"
            else:
                return await interaction.followup.send("❌ **Sebutkan judul lagu atau putar lagu.**", ephemeral=True)
        else:
            cleaned_title = self.clean_title_for_lyrics(search_query)
            search_query = cleaned_title

        await self.fetch_and_send_lyrics(interaction, search_query, original_artist, cleaned_title)

    async def fetch_and_send_lyrics(self, interaction: discord.Interaction, search_query: str, original_artist: str = "", cleaned_title: str = ""):
        """Enhanced lyrics fetching"""
        if not self.genius:
            return await interaction.followup.send("❌ **Fitur lirik tidak aktif.**", ephemeral=True)

        if not cleaned_title:
            cleaned_title = self.clean_title_for_lyrics(search_query)

        try:
            print(f"🎤 Mencari lirik untuk: '{cleaned_title}'")
            
            artist_to_use = original_artist
            
            if artist_to_use and ',' in artist_to_use:
                artist_to_use = artist_to_use.split(',')[0].strip()
            
            title_to_use = cleaned_title
            if ' - ' in cleaned_title:
                parts = cleaned_title.split(' - ', 1)
                if len(parts) == 2:
                    potential_artist = parts[0].strip()
                    title_only = parts[1].strip()
                    
                    if not artist_to_use:
                        artist_to_use = potential_artist
                    title_to_use = title_only
            
            title_to_use = re.sub(r'[^\w\s\-&]', ' ', title_to_use)
            title_to_use = re.sub(r'\s+', ' ', title_to_use).strip()
            
            print(f"🎯 Artist: '{artist_to_use}'")
            print(f"🎯 Title: '{title_to_use}'")
            
            song = None
            
            # Try multiple search strategies
            search_attempts = []
            
            if artist_to_use and title_to_use:
                search_attempts.append(f"{artist_to_use} {title_to_use}")
            
            if title_to_use:
                search_attempts.append(title_to_use)
            
            for attempt in search_attempts:
                print(f"🔍 Mencari: '{attempt}'")
                
                try:
                    found_song = self.genius.search_song(attempt)
                    
                    if found_song:
                        # Skip translations
                        translation_keywords = ['traducción', 'traduction', 'translation', 'übersetzung']
                        title_lower = found_song.title.lower()
                        
                        if not any(keyword in title_lower for keyword in translation_keywords):
                            print(f"✅ Ditemukan: '{found_song.title}' oleh '{found_song.artist}'")
                            song = found_song
                            break
                        
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    continue
            
            if not song:
                return await interaction.followup.send(
                    f"❌ **Lirik tidak ditemukan untuk:** {title_to_use}",
                    ephemeral=True
                )

            # Process lyrics
            lyrics_text = getattr(song, 'lyrics', '')
            if lyrics_text:
                # Clean up lyrics
                lyrics_text = re.sub(r'\[.*?\]', '', lyrics_text)
                lyrics_text = re.sub(r'\n\s*\n', '\n\n', lyrics_text)
                lyrics_text = lyrics_text.strip()
                
                if len(lyrics_text) > 3900:
                    lyrics_text = lyrics_text[:3890] + "\n\n**...(terpotong)**"
            else:
                lyrics_text = f"*Lirik tidak tersedia dalam format teks.*\n\n[Lihat di Genius]({song.url})"

            embed = discord.Embed(
                title=f"🎤 {song.title}",
                url=song.url,
                description=lyrics_text,
                color=0x1DB954
            )
            
            if hasattr(song, 'song_art_image_url') and song.song_art_image_url:
                embed.set_thumbnail(url=song.song_art_image_url)
            
            artist_name = getattr(song, 'artist', 'Unknown Artist')
            embed.set_footer(text=f"by {artist_name} • Sumber: Genius")
            
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ Lyrics search error: {e}")
            await interaction.followup.send("❌ **Terjadi error saat mencari lirik.**", ephemeral=True)

    @app_commands.command(name="nowplaying", description="🎵 Show currently playing song with enhanced controls")
    async def nowplaying(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        
        if not player.current:
            return await interaction.response.send_message(
                "❌ **No music is playing.**", ephemeral=True
            )
        
        control_view = EnhancedMusicControlView(self, interaction.guild.id)
        panel_view = EnhancedControlPanel(self, interaction.guild.id)
        
        await interaction.response.send_message(embed=control_view.get_enhanced_embed(), view=control_view)
        await interaction.followup.send("**🎛️ Enhanced Control Panel**", view=panel_view, ephemeral=True)

    # Di dalam kelas Music(commands.Cog)

    @app_commands.command(name="queue", description="📋 Menampilkan antrean musik (dengan halaman)")
    async def queue(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            player = self.get_player(interaction.guild.id)
            
            print("QUEUE_CMD: Defer berhasil. Menghitung durasi...")

            # --- PERBAIKAN DI SINI ---
            # Panggil langsung, BUKAN self.music_cog.calculate...
            total_duration = await self.calculate_total_duration(player.queue)
            
            print(f"QUEUE_CMD: Durasi dihitung: {total_duration}")

            # --- PERBAIKAN DI SINI ---
            # Berikan 'self' (objek Music), BUKAN self.music_cog
            view = QueuePaginatorView(player.queue, player.current, self, total_duration)
            
            initial_embed = view.create_queue_embed(total_duration)
            
            print("QUEUE_CMD: Embed dibuat. Mengirim followup...")
            
            await interaction.followup.send(embed=initial_embed, view=view)
            print("QUEUE_CMD: Followup terkirim.")
            
        except Exception as e:
            print(f"!!!!!!!!!! ERROR PADA /queue COMMAND !!!!!!!!!!!")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    f"❌ Terjadi error internal saat mengambil antrean: `{e}`", 
                    ephemeral=True
                )
            except:
                pass

    @app_commands.command(name="volume", description="🔊 Set music volume (0-150)")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 150]):
        player = self.get_player(interaction.guild.id)
        player.volume = level / 100
        
        vc = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if vc and hasattr(vc.source, 'volume'):
            vc.source.volume = level / 100
        
        volume_emoji = "🔊" if level > 70 else "🔉" if level > 30 else "🔈"
        await interaction.response.send_message(f"{volume_emoji} **Volume set to {level}%**")

    @app_commands.command(name="effects", description="🎧 Apply audio effects")
    @app_commands.choices(effect=[
        app_commands.Choice(name=effect, value=effect) 
        for effect in ["Normal", "Bass Boost", "Nightcore", "8D Audio", "Vaporwave"]
    ])
    async def effects(self, interaction: discord.Interaction, effect: app_commands.Choice[str]):
        player = self.get_player(interaction.guild.id)
        player.current_effect = effect.value
        
        effect_descriptions = {
            "Normal": "🎵 Clear audio without effects",
            "Bass Boost": "🎺 Enhanced low frequencies",
            "Nightcore": "⚡ High energy, fast-paced audio",
            "8D Audio": "🌀 Immersive spatial audio experience",
            "Vaporwave": "🌊 Chill, retro aesthetic sound"
        }
        
        await interaction.response.send_message(
            f"🎧 **Effect set to `{effect.name}`**\n"
            f"{effect_descriptions.get(effect.value, '')}\n"
            f"*Effect will apply to next song or when replaying current song.*"
        )

    @app_commands.command(name="autoplay", description="♾️ Toggle autoplay mode")
    async def autoplay(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        player.autoplay = not player.autoplay
        
        status = "ON" if player.autoplay else "OFF"
        await interaction.response.send_message(f"♾️ **Autoplay is now {status}**")

    @app_commands.command(name="remove", description="🗑️ Remove song from queue")
    async def remove(self, interaction: discord.Interaction, number: int):
        player = self.get_player(interaction.guild.id)
        
        if not player.queue or not (1 <= number <= len(player.queue)):
            return await interaction.response.send_message("❌ Invalid number.", ephemeral=True)
        
        removed = player.queue.pop(number - 1)
        removed_title = removed.get('title', 'Unknown')
        if len(removed_title) > 50:
            removed_title = removed_title[:47] + "..."
            
        await interaction.response.send_message(f"🗑️ **Removed:** `{removed_title}`")

    @app_commands.command(name="skip", description="⏭️ Skip current song")
    async def skip(self, interaction: discord.Interaction):
        vc = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        player = self.get_player(interaction.guild.id)
        
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            player.is_playing = False
            player.is_paused = False
            await interaction.response.send_message("⏭️ **Song skipped!**")
        else:
            await interaction.response.send_message("❌ **No song is playing.**", ephemeral=True)

    @app_commands.command(name="skipto", description="⏭️ Memainkan lagu pilihan dari antrean selanjutnya")
    @app_commands.describe(number="Nomor urut lagu di antrean yang ingin segera diputar")
    async def skipto(self, interaction: discord.Interaction, number: int):
        player = self.get_player(interaction.guild.id)
        vc = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        
        # 1. Validasi Voice Client
        if not vc or (not vc.is_playing() and not vc.is_paused()):
            return await interaction.response.send_message(
                "❌ **Tidak ada musik yang sedang diputar.**", ephemeral=True
            )
            
        # 2. Validasi Queue
        if not player.queue:
            return await interaction.response.send_message(
                "❌ **Antrean kosong.**", ephemeral=True
            )
            
        # 3. Validasi Nomor (input pengguna 1-indexed)
        if not (1 <= number <= len(player.queue)):
            return await interaction.response.send_message(
                f"❌ **Nomor tidak valid.** Silakan pilih 1 sampai {len(player.queue)}.", 
                ephemeral=True
            )
            
        # 4. Modifikasi queue: Pindahkan lagu yang dituju ke depan
        # Gunakan pop() untuk mengambil dan MENGHAPUS lagu dari posisinya saat ini
        # (number - 1 karena list 0-indexed)
        target_song = player.queue.pop(number - 1) 
        
        # Gunakan insert() untuk MENAMBAHKAN lagu itu di posisi 0 (paling depan)
        player.queue.insert(0, target_song)
            
        # 5. Matikan loop lagu (jika aktif) agar tidak mengulang lagu yang di-skip
        loop_status_msg = ""
        if player.loop:
            player.loop = False
            loop_status_msg = "\n*(Loop lagu saat ini telah dimatikan)*"
            
        # 6. Hentikan lagu saat ini. Ini akan memicu `after_song_callback` -> `play_next`
        #    `play_next` akan mengambil lagu [0] (yang baru saja kita insert)
        vc.stop()
        
        # 7. Beri respons
        target_title = target_song.get('title', 'Unknown')
        if len(target_title) > 50:
            target_title = target_title[:47] + "..."
            
        await interaction.response.send_message(
            f"⏭️ **OK! Memainkan** `{target_title}` {loop_status_msg}"
        )

    @app_commands.command(name="move", description="🔃 Memindahkan lagu di antrean ke posisi lain")
    @app_commands.describe(
        posisi_awal="Nomor urut lagu yang ingin dipindah (dimulai dari 1)",
        posisi_tujuan="Posisi baru untuk lagu tersebut (dimulai dari 1)"
    )
    async def move(self, interaction: discord.Interaction, posisi_awal: int, posisi_tujuan: int):
        player = self.get_player(interaction.guild.id)
        queue = player.queue
        queue_len = len(queue)
        
        # 1. Validasi antrean
        if queue_len == 0:
            return await interaction.response.send_message(
                "❌ **Antrean kosong, tidak ada yang bisa dipindah.**", ephemeral=True
            )
            
        # 2. Validasi posisi_awal
        if not (1 <= posisi_awal <= queue_len):
            return await interaction.response.send_message(
                f"❌ **Posisi awal tidak valid.** Harap pilih antara 1 dan {queue_len}.", 
                ephemeral=True
            )
            
        # 3. Validasi posisi_tujuan
        if not (1 <= posisi_tujuan <= queue_len):
            return await interaction.response.send_message(
                f"❌ **Posisi tujuan tidak valid.** Harap pilih antara 1 dan {queue_len}.", 
                ephemeral=True
            )
            
        # 4. Validasi kesamaan
        if posisi_awal == posisi_tujuan:
            return await interaction.response.send_message(
                "❌ **Lagu sudah ada di posisi tersebut.**", ephemeral=True
            )
            
        # 5. Logika Pemindahan (Gunakan 0-indexing)
        # Ambil dan hapus lagu dari posisi awal
        moved_song = queue.pop(posisi_awal - 1)
        
        # Masukkan lagu ke posisi tujuan
        queue.insert(posisi_tujuan - 1, moved_song)
        
        # 6. Kirim respons
        title = moved_song.get('title', 'Unknown')
        if len(title) > 40:
            title = title[:37] + "..."
            
        await interaction.response.send_message(
            f"🔃 **Berhasil!** Memindahkan `{title}` dari posisi **#{posisi_awal}** ke **#{posisi_tujuan}**."
        )

    @app_commands.command(name="clear", description="🗑️ Clear all songs from queue")
    async def clear(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        count = len(player.queue)
        player.queue.clear()
        await interaction.response.send_message(f"🗑️ **Cleared {count} songs from queue**")

    @app_commands.command(name="leave", description="👋 Disconnect bot from voice channel")
    async def leave(self, interaction: discord.Interaction):
        vc = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        
        if vc:
            await vc.disconnect()
            if interaction.guild.id in self.players:
                del self.players[interaction.guild.id]
            await interaction.response.send_message("👋 **Disconnected**")
        else:
            await interaction.response.send_message("❌ **Not connected**", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member == self.bot.user and before.channel and not after.channel:
            guild_id = before.channel.guild.id
            if guild_id in self.players:
                del self.players[guild_id]
                print(f"🧹 Player state for guild {before.channel.guild.name} cleaned.")

    @commands.Cog.listener()
    async def on_ready(self):
        print('✅ Enhanced Music Cog is ready')

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
# Maintenance update
