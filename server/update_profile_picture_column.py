"""
Script to update profile_picture column from MEDIUMTEXT to LONGBLOB
Run this script to fix the column type for profile pictures
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

def update_profile_picture_column():
    """Update profile_picture column to LONGBLOB"""
    print("Starting migration: Updating profile_picture column to LONGBLOB...")
    
    try:
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check current column type
        cursor.execute("""
            SELECT DATA_TYPE, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'profile_picture'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        
        if not result:
            print("✗ Column 'profile_picture' does not exist in users table")
            print("  Run add_profile_picture_column.py first")
            return False
        
        data_type, column_type = result
        print(f"Current column type: {column_type}")
        
        if data_type == 'longblob':
            print("✓ Column is already LONGBLOB - no update needed")
            return True
        
        print("Updating column to LONGBLOB...")
        
        # Drop old index if exists
        try:
            cursor.execute("DROP INDEX idx_users_profile_picture ON users")
            print("✓ Dropped old index")
        except:
            pass
        
        # Modify column to LONGBLOB
        cursor.execute("""
            ALTER TABLE users 
            MODIFY COLUMN profile_picture LONGBLOB NULL 
            COMMENT 'Profile picture stored as binary data'
        """)
        
        # Add new index
        cursor.execute("""
            CREATE INDEX idx_users_profile_picture 
            ON users(id)
        """)
        
        conn.commit()
        print("✓ Successfully updated profile_picture column to LONGBLOB")
        print("✓ Successfully recreated index")
        
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
    print("Update Profile Picture Column Type")
    print("=" * 60)
    print()
    
    success = update_profile_picture_column()
    
    if success:
        print("\nColumn updated successfully!")
        print("You can now upload profile pictures without size issues.")
    else:
        print("\nMigration failed. Please check the error messages above.")
    
    print()
