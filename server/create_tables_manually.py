#!/usr/bin/env python3
"""
Manually create tables
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

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("Creating tables...")
    
    # Drop existing tables if they exist
    print("\n1. Dropping existing tables...")
    cursor.execute("DROP TABLE IF EXISTS password_reset_tokens")
    cursor.execute("DROP TABLE IF EXISTS user_sessions")
    cursor.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    print("   ✓ Tables dropped")
    
    # Create users table
    print("\n2. Creating users table...")
    cursor.execute("""
        CREATE TABLE users (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          display_name VARCHAR(100) NOT NULL COMMENT 'Public display name visible to other users',
          email VARCHAR(255) NOT NULL COMMENT 'User email for authentication',
          password_hash VARCHAR(255) NOT NULL COMMENT 'Hashed password using bcrypt',
          email_verified BOOLEAN DEFAULT FALSE COMMENT 'Email verification status',
          is_active BOOLEAN DEFAULT TRUE COMMENT 'Account active status',
          last_login TIMESTAMP NULL DEFAULT NULL COMMENT 'Last login timestamp',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Account creation timestamp',
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
          PRIMARY KEY (id),
          UNIQUE KEY idx_email_unique (email),
          KEY idx_display_name (display_name),
          KEY idx_created_at (created_at),
          KEY idx_email_active (email, is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User accounts and authentication information'
    """)
    conn.commit()
    print("   ✓ Users table created")
    
    # Create sessions table
    print("\n3. Creating user_sessions table...")
    cursor.execute("""
        CREATE TABLE user_sessions (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          user_id BIGINT UNSIGNED NOT NULL,
          session_token VARCHAR(255) NOT NULL COMMENT 'Unique session token',
          ip_address VARCHAR(45) NULL COMMENT 'IP address of the session',
          user_agent VARCHAR(500) NULL COMMENT 'Browser/device user agent',
          expires_at TIMESTAMP NOT NULL COMMENT 'Session expiration time',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY idx_session_token (session_token),
          KEY idx_user_id (user_id),
          KEY idx_expires_at (expires_at),
          KEY idx_user_expires (user_id, expires_at),
          CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User session management'
    """)
    conn.commit()
    print("   ✓ User sessions table created")
    
    # Create password reset tokens table
    print("\n4. Creating password_reset_tokens table...")
    cursor.execute("""
        CREATE TABLE password_reset_tokens (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          user_id BIGINT UNSIGNED NOT NULL,
          token VARCHAR(255) NOT NULL COMMENT 'Reset token',
          expires_at TIMESTAMP NOT NULL COMMENT 'Token expiration time',
          used BOOLEAN DEFAULT FALSE COMMENT 'Whether token has been used',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY idx_token (token),
          KEY idx_user_id (user_id),
          KEY idx_expires_at (expires_at),
          CONSTRAINT fk_reset_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Password reset tokens'
    """)
    conn.commit()
    print("   ✓ Password reset tokens table created")
    
    # Update migration status
    print("\n5. Updating migration record...")
    cursor.execute("DELETE FROM schema_migrations WHERE migration_name = '001_create_users_table'")
    cursor.execute(
        "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
        ('001_create_users_table',)
    )
    conn.commit()
    print("   ✓ Migration record updated")
    
    print("\n" + "=" * 60)
    print("✓ All tables created successfully!")
    print("=" * 60)
    
    # Verify tables
    print("\nVerifying tables:")
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  ✓ {table[0]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
