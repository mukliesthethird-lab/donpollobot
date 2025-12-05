from imaplib import Commands
import sqlite3
from typing import Dict

from cogs.RPS import RPSGame

DB_PATH = 'database.db'

class RPS(Commands.Cog):
    """Rock Paper Scissors game cog"""
    
    def __init__(self, client):
        self.client = client
        self.active_games: Dict[int, RPSGame] = {}
        self.conn = sqlite3.connect('database.db')  # Koneksi ke database
        self._init_db()  # Inisialisasi tabel jika belum ada
        
    def _init_db(self):
        """Membuat tabel jika belum ada"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rps_stats (
                user_id INTEGER PRIMARY KEY,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

def set_custom_voice_channel(guild_id: int, channel_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO custom_voice (guild_id, channel_id)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id
    ''', (guild_id, channel_id))
    conn.commit()
    conn.close()

def get_custom_voice_channel(guild_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id FROM custom_voice WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


# Maintenance update
