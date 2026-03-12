"""
Create admin system database tables
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

def create_admin_tables():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("1. Adding is_admin column to users table...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS is_admin TINYINT(1) DEFAULT 0
        """)
        
        # Set admin for jaivikppatel@gmail.com
        cursor.execute("""
            UPDATE users 
            SET is_admin = 1 
            WHERE email = 'jaivikppatel@gmail.com'
        """)
        
        print("2. Creating scoring_profiles table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scoring_profiles (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                is_default TINYINT(1) DEFAULT 0,
                point_distribution JSON NOT NULL COMMENT 'JSON with rank->points mapping',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_is_default (is_default)
            )
        """)
        
        # Create default scoring profile
        cursor.execute("""
            INSERT INTO scoring_profiles (name, description, is_default, point_distribution)
            VALUES (
                'Standard F1 Scoring',
                'Standard F1-style points: Top 10 get points',
                1,
                '{"1": 25, "2": 18, "3": 15, "4": 12, "5": 10, "6": 8, "7": 6, "8": 4, "9": 2, "10": 1}'
            )
        """)
        
        print("3. Creating ipl_game_schedule table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ipl_game_schedule (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                match_name VARCHAR(255) NOT NULL,
                match_date DATE NOT NULL,
                match_time TIME,
                venue VARCHAR(255),
                scoring_profile_id BIGINT UNSIGNED,
                is_completed TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (scoring_profile_id) REFERENCES scoring_profiles(id),
                INDEX idx_match_date (match_date),
                INDEX idx_is_completed (is_completed)
            )
        """)
        
        print("4. Creating match_rankings table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_rankings (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                game_id BIGINT UNSIGNED NOT NULL,
                user_id BIGINT UNSIGNED NOT NULL,
                user_rank INT NOT NULL,
                points_earned INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES ipl_game_schedule(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE KEY unique_game_user (game_id, user_id),
                INDEX idx_game_id (game_id),
                INDEX idx_user_id (user_id)
            )
        """)
        
        conn.commit()
        print("\n✓ All admin tables created successfully!")
        
        # Check if admin user exists
        cursor.execute("SELECT id, display_name, is_admin FROM users WHERE email = 'jaivikppatel@gmail.com'")
        admin = cursor.fetchone()
        if admin:
            print(f"✓ Admin user: {admin[1]} (ID: {admin[0]}) - Admin: {bool(admin[2])}")
        else:
            print("! Admin user jaivikppatel@gmail.com not found - please register this account")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    create_admin_tables()
