#!/usr/bin/env python3
"""
Check database tables
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
    
    print(f"Connected to database: {DB_CONFIG['database']}")
    print("\nTables in database:")
    print("-" * 50)
    
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    if tables:
        for table in tables:
            print(f"  - {table[0]}")
            
            # Show table structure
            cursor.execute(f"DESCRIBE {table[0]}")
            columns = cursor.fetchall()
            for col in columns:
                print(f"      {col[0]} ({col[1]})")
            print()
    else:
        print("  No tables found!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
