# Database Migrations

This directory contains SQL migration scripts for the scorecard application database.

## Running Migrations

### Using MariaDB CLI

```bash
# Connect to your MariaDB database
mysql -u your_username -p your_database_name

# Run the migration
mysql -u your_username -p your_database_name < migrations/001_create_users_table.sql
```

### Using Python Script

```bash
# Run all pending migrations
python run_migrations.py
```

## Migration Files

- `001_create_users_table.sql` - Creates users and user_sessions tables

## Security Notes

1. **Password Hashing**: Always use bcrypt with a minimum cost factor of 12
   ```python
   import bcrypt
   password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
   ```

2. **Email Validation**: Validate email format before storing

3. **SQL Injection Prevention**: Always use parameterized queries
   ```python
   cursor.execute("INSERT INTO users (display_name, email, password_hash) VALUES (?, ?, ?)", 
                  (display_name, email, password_hash))
   ```

4. **Session Management**: 
   - Set appropriate session expiration times (e.g., 24 hours)
   - Implement session token rotation
   - Clear expired sessions regularly

## Database Configuration

Example connection configuration for MariaDB:

```python
import mysql.connector
from mysql.connector import Error

config = {
    'host': 'localhost',
    'database': 'scorecard_db',
    'user': 'your_username',
    'password': 'your_password',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'use_pure': True
}

connection = mysql.connector.connect(**config)
```

## Best Practices

1. Never store passwords in plain text
2. Use HTTPS in production
3. Implement rate limiting for login attempts
4. Add email verification before activating accounts
5. Implement password strength requirements
6. Use environment variables for database credentials
