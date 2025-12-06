import sqlite3
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime

# Load Environment Variables
load_dotenv()

SQLITE_DB = "database.db"

# MySQL Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "donpollobot_db")
DB_PORT = os.getenv("DB_PORT", "3306")

def get_mysql_conn():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"❌ MySQL Connection Error: {e}")
        return None



def create_tables(mysql_conn):
    cursor = mysql_conn.cursor()
    print("--- Creating Tables if they don't exist ---")
    
    # Economy Tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS slot_users (
        user_id BIGINT PRIMARY KEY,
        balance BIGINT DEFAULT 500,
        total_wins INT DEFAULT 0,
        total_losses INT DEFAULT 0,
        last_daily TEXT,
        last_work TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS loans (
        user_id BIGINT PRIMARY KEY,
        amount BIGINT,
        due_date TEXT
    )
    ''')
    
    # Fishing Tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fish_inventory (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT,
        fish_name TEXT,
        rarity TEXT,
        weight DECIMAL(10, 2),
        price INT,
        caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fishing_rods (
        user_id BIGINT,
        rod_name VARCHAR(255),
        level INT DEFAULT 0,
        PRIMARY KEY (user_id, rod_name)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fishing_profile (
        user_id BIGINT PRIMARY KEY,
        equipped_rod TEXT,
        total_catches INT DEFAULT 0
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fishing_materials (
        user_id BIGINT,
        material_name VARCHAR(255),
        amount INT DEFAULT 0,
        PRIMARY KEY (user_id, material_name)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fishing_items (
        user_id BIGINT,
        item_name VARCHAR(255),
        amount INT DEFAULT 0,
        PRIMARY KEY (user_id, item_name)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fishing_quests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT,
        quest_type TEXT,
        target_criteria TEXT,
        target_value INT,
        progress INT DEFAULT 0,
        reward_amount INT,
        is_claimed BOOLEAN DEFAULT 0,
        created_at DATE,
        quest_period TEXT,
        expiration_date TIMESTAMP,
        reward_type TEXT DEFAULT 'coin',
        reward_name TEXT
    )
    ''')

    # Ticket Tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS guild_config (
        guild_id BIGINT PRIMARY KEY,
        category_id BIGINT,
        log_channel_id BIGINT,
        panel_channel_id BIGINT,
        panel_message_id BIGINT,
        support_role_id BIGINT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS active_tickets (
        channel_id BIGINT PRIMARY KEY,
        guild_id BIGINT,
        user_id BIGINT,
        created_at TEXT,
        reason TEXT
    )
    ''')

    # RPS Tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rps_stats (
        user_id BIGINT PRIMARY KEY,
        total_games INT DEFAULT 0,
        games_won INT DEFAULT 0,
        games_lost INT DEFAULT 0,
        rounds_won INT DEFAULT 0,
        rounds_lost INT DEFAULT 0,
        rounds_tied INT DEFAULT 0,
        last_played BIGINT DEFAULT 0
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rps_sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        player1_id BIGINT,
        player2_id BIGINT,
        winner_id BIGINT,
        player1_score INT,
        player2_score INT,
        rounds_played INT,
        timestamp BIGINT
    )
    ''')

    # WhosLying Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS game_channels
                 (channel_id BIGINT PRIMARY KEY, guild_id BIGINT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS lobby_messages
                 (channel_id BIGINT PRIMARY KEY, message_id BIGINT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS game_players
                 (channel_id BIGINT, user_id BIGINT, 
                  PRIMARY KEY (channel_id, user_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_games
                 (channel_id BIGINT PRIMARY KEY,
                  theme TEXT, word TEXT, session INT,
                  impostor_id BIGINT, phase TEXT)''')
                  
    # Warn Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warnings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            moderator_id BIGINT NOT NULL,
            moderator_name TEXT,
            reason TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            case_number INT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warn_cases (
            guild_id BIGINT PRIMARY KEY,
            current_case INT DEFAULT 0
        )
    ''')
    
    mysql_conn.commit()
    print("✅ Tables initialized.")

def migrate_economy(sqlite_conn, mysql_conn):
    print("--- Migrating Economy ---")
    s_cursor = sqlite_conn.cursor()
    m_cursor = mysql_conn.cursor()

    # slot_users
    try:
        s_cursor.execute("SELECT user_id, balance, total_wins, total_losses, last_daily, last_work, created_at FROM slot_users")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO slot_users (user_id, balance, total_wins, total_losses, last_daily, last_work, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE balance=%s
            ''', (*row, row[1])) 
        print(f"✅ Migrated {len(rows)} users from slot_users")
    except Exception as e:
        print(f"⚠️ Error migrating slot_users: {e}")

    # loans
    try:
        s_cursor.execute("SELECT user_id, amount, due_date FROM loans")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO loans (user_id, amount, due_date)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE amount=%s
            ''', (*row, row[1]))
        print(f"✅ Migrated {len(rows)} loans")
    except Exception as e:
        print(f"⚠️ Error migrating loans: {e}")
        
    mysql_conn.commit()

def migrate_fishing(sqlite_conn, mysql_conn):
    print("--- Migrating Fishing ---")
    s_cursor = sqlite_conn.cursor()
    m_cursor = mysql_conn.cursor()

    # fishing_profile
    try:
        s_cursor.execute("SELECT user_id, equipped_rod, total_catches FROM fishing_profile")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO fishing_profile (user_id, equipped_rod, total_catches)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE total_catches=%s
            ''', (*row, row[2]))
        print(f"✅ Migrated {len(rows)} fishing_profiles")
    except Exception as e:
        print(f"⚠️ Error migrating fishing_profile: {e}")

    # fishing_rods
    try:
        s_cursor.execute("SELECT user_id, rod_name, level FROM fishing_rods")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO fishing_rods (user_id, rod_name, level)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE level=%s
            ''', (*row, row[2]))
        print(f"✅ Migrated {len(rows)} fishing_rods")
    except Exception as e:
        print(f"⚠️ Error migrating fishing_rods: {e}")

    # fishing_materials
    try:
        s_cursor.execute("SELECT user_id, material_name, amount FROM fishing_materials")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO fishing_materials (user_id, material_name, amount)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE amount=%s
            ''', (*row, row[2]))
        print(f"✅ Migrated {len(rows)} fishing_materials")
    except Exception as e:
        print(f"⚠️ Error migrating fishing_materials: {e}")

    # fishing_items
    try:
        s_cursor.execute("SELECT user_id, item_name, amount FROM fishing_items")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO fishing_items (user_id, item_name, amount)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE amount=%s
            ''', (*row, row[2]))
        print(f"✅ Migrated {len(rows)} fishing_items")
    except Exception as e:
        print(f"⚠️ Error migrating fishing_items: {e}")
        
    # fish_inventory
    try:
        s_cursor.execute("SELECT user_id, fish_name, rarity, weight, price FROM fish_inventory")
        rows = s_cursor.fetchall()
        count = 0
        for row in rows:
            m_cursor.execute('''
                INSERT INTO fish_inventory (user_id, fish_name, rarity, weight, price)
                VALUES (%s, %s, %s, %s, %s)
            ''', row)
            count += 1
        print(f"✅ Migrated {count} fish items")
    except Exception as e:
        print(f"⚠️ Error migrating fish_inventory: {e}")
        
    # fishing_quests
    try:
        # Check if table exists in SQLite first
        s_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fishing_quests'")
        if s_cursor.fetchone():
            s_cursor.execute("SELECT user_id, quest_type, target_criteria, target_value, progress, reward_amount, is_claimed, created_at FROM fishing_quests")
            rows = s_cursor.fetchall()
            count = 0
            for row in rows:
                m_cursor.execute('''
                    INSERT INTO fishing_quests (user_id, quest_type, target_criteria, target_value, progress, reward_amount, is_claimed, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', row)
                count += 1
            print(f"✅ Migrated {count} fishing_quests")
        else:
            print("ℹ️ No fishing_quests table in SQLite.")
            
    except Exception as e:
        print(f"⚠️ Error migrating fishing_quests: {e}")

    mysql_conn.commit()

def migrate_ticket(sqlite_conn, mysql_conn):
    print("--- Migrating Ticket ---")
    s_cursor = sqlite_conn.cursor()
    m_cursor = mysql_conn.cursor()
    
    try:
        s_cursor.execute("SELECT guild_id, category_id, log_channel_id, panel_channel_id, panel_message_id, support_role_id FROM guild_config")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO guild_config (guild_id, category_id, log_channel_id, panel_channel_id, panel_message_id, support_role_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE category_id=%s
            ''', (*row, row[1]))
        print(f"✅ Migrated {len(rows)} guild configs")
    except Exception as e:
        print(f"⚠️ Error migrating guild_config: {e}")

    try:
        s_cursor.execute("SELECT channel_id, guild_id, user_id, created_at, reason FROM active_tickets")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO active_tickets (channel_id, guild_id, user_id, created_at, reason)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE reason=%s
            ''', (*row, row[4]))
        print(f"✅ Migrated {len(rows)} active tickets")
    except Exception as e:
        print(f"⚠️ Error migrating active_tickets: {e}")
    
    mysql_conn.commit()

def migrate_rps(sqlite_conn, mysql_conn):
    print("--- Migrating RPS ---")
    s_cursor = sqlite_conn.cursor()
    m_cursor = mysql_conn.cursor()
    
    try:
        s_cursor.execute("SELECT user_id, total_games, games_won, games_lost, rounds_won, rounds_lost, rounds_tied, last_played FROM rps_stats")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO rps_stats (user_id, total_games, games_won, games_lost, rounds_won, rounds_lost, rounds_tied, last_played)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE total_games=%s
            ''', (*row, row[1]))
        print(f"✅ Migrated {len(rows)} RPS stats")
    except Exception as e:
        print(f"⚠️ Error migrating rps_stats: {e}")

    mysql_conn.commit()

def migrate_whoslying(sqlite_conn, mysql_conn):
    print("--- Migrating WhosLying ---")
    s_cursor = sqlite_conn.cursor()
    m_cursor = mysql_conn.cursor()
    
    # game_channels
    try:
        s_cursor.execute("SELECT channel_id, guild_id FROM game_channels")
        for row in s_cursor.fetchall():
            m_cursor.execute("INSERT IGNORE INTO game_channels VALUES (%s, %s)", row)
        print("✅ Migrated game_channels")
    except Exception as e:
        print(f"⚠️ Error game_channels: {e}")

    # lobby_messages
    try:
        s_cursor.execute("SELECT channel_id, message_id FROM lobby_messages")
        for row in s_cursor.fetchall():
            m_cursor.execute("INSERT IGNORE INTO lobby_messages VALUES (%s, %s)", row)
        print("✅ Migrated lobby_messages")
    except Exception as e:
        print(f"⚠️ Error lobby_messages: {e}")
        
    mysql_conn.commit()

def migrate_warn(sqlite_conn, mysql_conn):
    print("--- Migrating Warn ---")
    s_cursor = sqlite_conn.cursor()
    m_cursor = mysql_conn.cursor()
    
    # warnings
    try:
        # Check existing columns in sqlite
        s_cursor.execute("PRAGMA table_info(warnings)")
        cols = [c[1] for c in s_cursor.fetchall()]
        
        query = "SELECT guild_id, user_id, moderator_id, reason, timestamp, case_number"
        has_mod_name = 'moderator_name' in cols
        if has_mod_name:
            query += ", moderator_name"
        query += " FROM warnings"
        
        s_cursor.execute(query)
        rows = s_cursor.fetchall()
        count = 0
        for row in rows:
            if has_mod_name:
                # row structure: g_id, u_id, m_id, reason, time, case, mod_name
                # insert expects: g_id, u_id, m_id, mod_name, reason, time, case
                m_cursor.execute('''
                    INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp, case_number, moderator_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
            else:
                m_cursor.execute('''
                    INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp, case_number, moderator_name)
                    VALUES (%s, %s, %s, %s, %s, %s, 'Unknown')
                ''', (row[0], row[1], row[2], row[3], row[4], row[5]))
            count += 1
        print(f"✅ Migrated {count} warnings")
    except Exception as e:
        print(f"⚠️ Error migrating warnings: {e}")

    # warn_cases
    try:
        s_cursor.execute("SELECT guild_id, current_case FROM warn_cases")
        rows = s_cursor.fetchall()
        for row in rows:
            m_cursor.execute('''
                INSERT INTO warn_cases (guild_id, current_case)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE current_case=%s
            ''', (*row, row[1]))
        print(f"✅ Migrated {len(rows)} warn_cases")
    except Exception as e:
        print(f"⚠️ Error migrating warn_cases: {e}")
        
    mysql_conn.commit()

def main():
    if not os.path.exists(SQLITE_DB):
        print(f"❌ SQLite database '{SQLITE_DB}' not found. Nothing to migrate.")
        return

    print(f"📂 Found SQLite DB: {SQLITE_DB}")
    
    # Connect
    s_conn = sqlite3.connect(SQLITE_DB)
    m_conn = get_mysql_conn()
    
    if not m_conn:
        print("❌ Cannot connect to MySQL. Check your .env file.")
        return

    try:
        create_tables(m_conn)
        migrate_economy(s_conn, m_conn)
        migrate_fishing(s_conn, m_conn)
        migrate_ticket(s_conn, m_conn)
        migrate_rps(s_conn, m_conn)
        migrate_whoslying(s_conn, m_conn)
        migrate_warn(s_conn, m_conn)
        
        print("\n🎉 Full Migration Complete!")
    except Exception as e:
        print(f"\n❌ Migration Failed: {e}")
    finally:
        s_conn.close()
        m_conn.close()

if __name__ == "__main__":
    main()
