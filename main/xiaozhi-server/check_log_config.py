#!/usr/bin/env python3
"""
Script to check and fix log configuration in database
"""
import mysql.connector
import json
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

def connect_to_database():
    """Connect to the Railway MySQL database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("Successfully connected to Railway MySQL database")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

def check_log_parameters(connection):
    """Check log-related parameters"""
    cursor = connection.cursor()
    
    try:
        # Check for log-related parameters
        cursor.execute("SELECT id, param_code, param_value FROM sys_params WHERE param_code LIKE '%log%'")
        rows = cursor.fetchall()
        
        print("=== Log-related Parameters ===")
        for row in rows:
            print(f"ID: {row[0]} | Code: {row[1]} | Value: {row[2]}")
            
        return rows
    except Error as e:
        print(f"Error querying log parameters: {e}")
        return []
    finally:
        cursor.close()

def fix_log_level_if_needed(connection):
    """Fix log level if it's corrupted"""
    cursor = connection.cursor()
    
    try:
        # Check if there's a corrupted log_level parameter
        cursor.execute("SELECT id, param_code, param_value FROM sys_params WHERE param_value LIKE '%http%' AND param_value LIKE '%ota%'")
        corrupted_rows = cursor.fetchall()
        
        if corrupted_rows:
            print(f"\nFound {len(corrupted_rows)} corrupted parameters:")
            for row in corrupted_rows:
                print(f"  ID: {row[0]} | Code: {row[1]} | Value: {row[2]}")
            
            # Fix the corrupted log level
            for row in corrupted_rows:
                if 'log' in row[1].lower():  # If it's a log-related parameter
                    print(f"\nFixing parameter {row[1]} (ID: {row[0]})")
                    cursor.execute(
                        "UPDATE sys_params SET param_value = %s, update_date = NOW() WHERE id = %s",
                        ("INFO", row[0])
                    )
                    connection.commit()
                    print(f"✅ Fixed: {row[1]} set to 'INFO'")
        else:
            print("\nNo corrupted log parameters found.")
            
    except Error as e:
        print(f"Error fixing log parameters: {e}")
        connection.rollback()
    finally:
        cursor.close()

def check_all_params_with_urls(connection):
    """Check all parameters that might have URLs incorrectly"""
    cursor = connection.cursor()
    
    try:
        cursor.execute("SELECT id, param_code, param_value FROM sys_params WHERE param_value LIKE '%http%'")
        rows = cursor.fetchall()
        
        print(f"\n=== All Parameters with HTTP URLs ===")
        for row in rows:
            print(f"ID: {row[0]} | Code: {row[1]} | Value: {row[2]}")
            
    except Error as e:
        print(f"Error querying URL parameters: {e}")
    finally:
        cursor.close()

def main():
    """Main function"""
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        check_log_parameters(connection)
        check_all_params_with_urls(connection)
        fix_log_level_if_needed(connection)
        
        # Check again after fix
        print("\n" + "="*50)
        print("After fix:")
        check_log_parameters(connection)
        
    except Error as e:
        print(f"Error during database operations: {e}")
    
    finally:
        if connection.is_connected():
            connection.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()