#!/usr/bin/env python3
"""
Script to fix the corrupted log.log_level parameter
"""
import mysql.connector
from mysql.connector import Error

# Database configuration
DB_CONFIG = {
    'host': 'nozomi.proxy.rlwy.net',
    'port': 25037,
    'database': 'railway',
    'user': 'root',
    'password': 'OcaVNLKcwNdyElfaeUPqvvfYZiiEHgdm',
    'ssl_disabled': True,
    'use_unicode': True,
    'charset': 'utf8mb4'
}

def fix_log_level():
    """Fix the corrupted log.log_level parameter"""
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Check current value
        cursor.execute("SELECT param_value FROM sys_params WHERE param_code = 'log.log_level'")
        current_value = cursor.fetchone()
        print(f"Current log.log_level value: {current_value[0] if current_value else 'NOT FOUND'}")
        
        # Fix the value
        cursor.execute(
            "UPDATE sys_params SET param_value = %s, update_date = NOW() WHERE param_code = %s",
            ("INFO", "log.log_level")
        )
        connection.commit()
        
        # Verify the fix
        cursor.execute("SELECT param_value FROM sys_params WHERE param_code = 'log.log_level'")
        new_value = cursor.fetchone()
        print(f"Fixed log.log_level value: {new_value[0] if new_value else 'NOT FOUND'}")
        
        print("SUCCESS: log.log_level has been fixed!")
        
    except Error as e:
        print(f"Error: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    fix_log_level()