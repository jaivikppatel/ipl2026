"""
Update match_rankings table to use fantasy_points instead of rank
"""
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': int(os.getenv('DB_PORT', 3306))
}

def update_rankings_table():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("Updating match_rankings table...")
        
        # Add fantasy_points column
        cursor.execute("""
            ALTER TABLE match_rankings 
            ADD COLUMN IF NOT EXISTS fantasy_points INT NOT NULL DEFAULT 0 AFTER user_id
        """)
        
        # Modify user_rank to be auto-calculated (we'll calculate it in application)
        # Keep it as INT but we'll populate it based on fantasy_points
        
        print("✓ Table updated successfully!")
        
        # Also update scoring_profiles to support more features
        cursor.execute("""
            ALTER TABLE scoring_profiles
            ADD COLUMN IF NOT EXISTS is_multiplier TINYINT(1) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS multiplier DECIMAL(3,2) DEFAULT 1.0,
            ADD COLUMN IF NOT EXISTS max_ranks INT DEFAULT 10
        """)
        
        conn.commit()
        print("✓ Scoring profiles enhanced!")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    update_rankings_table()
