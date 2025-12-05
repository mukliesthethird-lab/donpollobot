import sqlite3

# Koneksi ke database (akan otomatis membuat file database.db jika belum ada)
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Contoh: Tabel untuk menyimpan konfigurasi custom voice per guild
cursor.execute('''
CREATE TABLE IF NOT EXISTS custom_voice (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL
)
''')

# Simpan dan tutup koneksi
conn.commit()
conn.close()

print("Database berhasil dibuat.")

# Maintenance update
