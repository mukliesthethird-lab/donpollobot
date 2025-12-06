import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# MySQL Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "donpollobot_db")
DB_PORT = os.getenv("DB_PORT", "3306")

def check_db():
    print(f"🔌 Connecting to MySQL Database: {DB_NAME}...")
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        cursor = conn.cursor()
        

        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Database Summary for '{DB_NAME}':")
        print("-" * 40)
        print(f"{'Table Name':<30} | {'Row Count':<10}")
        print("-" * 40)
        
        total_rows = 0
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"{table:<30} | {count:<10}")
                total_rows += count
            except mysql.connector.Error as err:
                print(f"{table:<30} | ❌ Error ({err.errno})")
        
        print("-" * 40)
        print(f"Total Rows Checked: {total_rows}")

        
        # Show top rich users as a sample
        print("\n💰 Top 3 Richest Users (Economy):")
        cursor.execute("SELECT user_id, balance FROM slot_users ORDER BY balance DESC LIMIT 3")
        for user_id, bal in cursor.fetchall():
            print(f"- User {user_id}: {bal:,} coins")

        conn.close()
        print("\n✅ Verification Complete!")
        
    except mysql.connector.Error as err:
        print(f"❌ Connection Failed: {err}")
        print("💡 Hint: Check your .env file credentials.")

if __name__ == "__main__":
    check_db()
