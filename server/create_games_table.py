"""
Manually create the ipl_matches table for IPL fantasy points tracking
"""
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': int(os.getenv('DB_PORT', 3306))
}

# F1-style points system
POINTS_SYSTEM = {
    1: 25,
    2: 18,
    3: 15,
    4: 12,
    5: 10,
    6: 8,
    7: 6,
    8: 4,
    9: 2,
    10: 1
}

def get_points_for_rank(rank):
    """Get points for a given rank (11+ gets 0 points)"""
    return POINTS_SYSTEM.get(rank, 0)

def create_games_table():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("Dropping old games table...")
        cursor.execute("DROP TABLE IF EXISTS games")
        
        print("Creating ipl_matches table...")
        cursor.execute("""
            CREATE TABLE ipl_matches (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT UNSIGNED NOT NULL,
                match_name VARCHAR(255) NOT NULL COMMENT 'e.g., MI vs CSK, RCB vs KKR',
                match_date DATE NOT NULL,
                user_rank INT NOT NULL COMMENT 'User ranking in this match (1-10+)',
                points INT NOT NULL COMMENT 'Points earned based on rank',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id),
                INDEX idx_match_date (match_date),
                INDEX idx_points (points)
            )
        """)
        
        conn.commit()
        print("✓ ipl_matches table created successfully!")
        
        # Get the first user to add sample data
        cursor.execute("SELECT id, display_name FROM users LIMIT 1")
        user = cursor.fetchone()
        
        if user:
            user_id, display_name = user
            print(f"Adding sample IPL fantasy data for user: {display_name} (ID: {user_id})")
            
            # Sample IPL matches with various rankings
            sample_matches = [
                ('MI vs CSK', '2026-01-10', 1),    # 1st place = 25 points
                ('RCB vs KKR', '2026-01-12', 3),   # 3rd place = 15 points
                ('DC vs RR', '2026-01-13', 2),     # 2nd place = 18 points
                ('GT vs LSG', '2026-01-15', 5),    # 5th place = 10 points
                ('PBKS vs SRH', '2026-01-16', 4),  # 4th place = 12 points
                ('MI vs RCB', '2026-01-14', 8),    # 8th place = 4 points
                ('CSK vs DC', '2026-01-11', 1),    # 1st place = 25 points
            ]
            
            for match_name, match_date, rank in sample_matches:
                points = get_points_for_rank(rank)
                cursor.execute("""
                    INSERT INTO ipl_matches (user_id, match_name, match_date, user_rank, points)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, match_name, match_date, rank, points))
            
            conn.commit()
            total_points = sum(get_points_for_rank(rank) for _, _, rank in sample_matches)
            print(f"✓ Sample data added! Total points: {total_points}")
        else:
            print("! No users found - skipping sample data")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    create_games_table()
