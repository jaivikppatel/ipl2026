#!/usr/bin/env python3
"""
Database Migration Runner
Executes SQL migration files in order
"""

import os
import sys
import mysql.connector
from mysql.connector import Error
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'scorecard_db'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def create_migrations_table(cursor):
    """Create a table to track applied migrations"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS `schema_migrations` (
            `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            `migration_name` VARCHAR(255) NOT NULL UNIQUE,
            `applied_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            KEY `idx_migration_name` (`migration_name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    print("✓ Migrations tracking table ready")

def get_applied_migrations(cursor):
    """Get list of already applied migrations"""
    cursor.execute("SELECT migration_name FROM schema_migrations ORDER BY migration_name")
    return {row[0] for row in cursor.fetchall()}

def get_migration_files():
    """Get all SQL migration files sorted by name"""
    migrations_dir = Path(__file__).parent / 'migrations'
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return []
    
    sql_files = sorted(migrations_dir.glob('*.sql'))
    return [(f.stem, f) for f in sql_files]

def run_migration(cursor, migration_name, migration_file):
    """Execute a single migration file"""
    print(f"Running migration: {migration_name}...")
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Split by semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement and not statement.startswith('--'):
                cursor.execute(statement)
        
        # Record the migration as applied
        cursor.execute(
            "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
            (migration_name,)
        )
        
        print(f"✓ Migration {migration_name} applied successfully")
        return True
        
    except Error as e:
        print(f"❌ Error running migration {migration_name}: {e}")
        return False

def main():
    """Main migration runner"""
    print("=" * 60)
    print("Database Migration Runner")
    print("=" * 60)
    
    try:
        # Connect to database
        print(f"\nConnecting to database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
        connection = mysql.connector.connect(**DB_CONFIG)
        
        if connection.is_connected():
            cursor = connection.cursor()
            print("✓ Database connection established")
            
            # Create migrations tracking table
            create_migrations_table(cursor)
            connection.commit()
            
            # Get applied migrations
            applied_migrations = get_applied_migrations(cursor)
            print(f"\nApplied migrations: {len(applied_migrations)}")
            
            # Get all migration files
            migration_files = get_migration_files()
            print(f"Total migration files: {len(migration_files)}\n")
            
            if not migration_files:
                print("No migration files found.")
                return
            
            # Run pending migrations
            pending_count = 0
            for migration_name, migration_file in migration_files:
                if migration_name not in applied_migrations:
                    if run_migration(cursor, migration_name, migration_file):
                        connection.commit()
                        pending_count += 1
                    else:
                        connection.rollback()
                        print(f"\n❌ Migration failed. Rolling back...")
                        sys.exit(1)
                else:
                    print(f"⊘ Skipping already applied: {migration_name}")
            
            print("\n" + "=" * 60)
            if pending_count > 0:
                print(f"✓ Successfully applied {pending_count} migration(s)")
            else:
                print("✓ All migrations up to date!")
            print("=" * 60)
            
    except Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
        
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("\n✓ Database connection closed")

if __name__ == "__main__":
    main()
