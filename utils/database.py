import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

load_dotenv()

db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "donpollobot"),
    "port": int(os.getenv("DB_PORT", 3306))
}

# Create a connection pool to handle multiple connections efficiently
# This avoids "Lost connection to MySQL server" errors during high load
connection_pool = None

def get_db_connection():
    global connection_pool
    if connection_pool is None:
        try:
            connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="bot_pool",
                pool_size=5,
                pool_reset_session=True,
                **db_config
            )
            print("✅ Database connection pool created")
        except mysql.connector.Error as err:
            print(f"❌ Error creating connection pool: {err}")
            return None

    try:
        return connection_pool.get_connection()
    except mysql.connector.Error as err:
        print(f"❌ Error getting connection from pool: {err}")
        return None
