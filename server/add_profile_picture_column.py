"""
Script to add profile_picture column to users table
Run this script to update the database schema for profile pictures
"""

import os
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': int(os.getenv('DB_PORT', 3306))
}

def add_profile_picture_column():
    """Add profile_picture column to users table"""
    print("Starting migration: Adding profile_picture column to users table...")
    
    try:
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'profile_picture'
        """, (DB_CONFIG['database'],))
        
        column_exists = cursor.fetchone()[0] > 0
        
        if column_exists:
            print("✓ Column 'profile_picture' already exists in users table")
        else:
            print("Adding profile_picture column...")
            
            # Add profile_picture column
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN profile_picture LONGBLOB NULL 
                COMMENT 'Profile picture stored as binary data'
            """)
            
            # Add index for faster queries
            cursor.execute("""
                CREATE INDEX idx_users_profile_picture 
                ON users(id)
            """)
            
            conn.commit()
            print("✓ Successfully added profile_picture column")
            print("✓ Successfully added index for profile_picture")
        
        cursor.close()
        conn.close()
        
        print("\n✓ Migration completed successfully!")
        return True
        
    except mysql.connector.Error as e:
        print(f"\n✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Profile Picture Migration Script")
    print("=" * 60)
    print()
    
    success = add_profile_picture_column()
    
    if success:
        print("\nYou can now restart your server to use profile pictures!")
    else:
        print("\nMigration failed. Please check the error messages above.")
    
    print()
