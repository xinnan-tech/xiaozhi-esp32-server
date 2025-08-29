#!/usr/bin/env python3
"""
Script to check the actual database table structures
"""
import mysql.connector
import json
from mysql.connector import Error

# Database configuration from application-dev.yml
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

def describe_table(connection, table_name):
    """Describe the structure of a table"""
    cursor = connection.cursor()
    try:
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        print(f"\n=== Table: {table_name} ===")
        for col in columns:
            print(f"  {col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
        return [col[0] for col in columns]
    except Error as e:
        print(f"Error describing table {table_name}: {e}")
        return []
    finally:
        cursor.close()

def check_sys_params(connection):
    """Check sys_params table structure and content"""
    cursor = connection.cursor()
    columns = describe_table(connection, 'sys_params')
    
    try:
        # Get a few sample records
        cursor.execute("SELECT * FROM sys_params LIMIT 10")
        rows = cursor.fetchall()
        print(f"\nSample data from sys_params:")
        for row in rows:
            row_dict = dict(zip(columns, row))
            print(f"  {json.dumps(row_dict, indent=2, default=str)}")
    except Error as e:
        print(f"Error querying sys_params: {e}")
    finally:
        cursor.close()

def check_ai_model_config(connection):
    """Check ai_model_config table structure and content"""
    cursor = connection.cursor()
    columns = describe_table(connection, 'ai_model_config')
    
    try:
        # Get LLM configs
        cursor.execute("SELECT * FROM ai_model_config WHERE model_type = 'LLM' LIMIT 5")
        rows = cursor.fetchall()
        print(f"\nLLM configurations from ai_model_config:")
        for row in rows:
            row_dict = dict(zip(columns, row))
            print(f"  {json.dumps(row_dict, indent=2, default=str)}")
    except Error as e:
        print(f"Error querying ai_model_config: {e}")
    finally:
        cursor.close()

def main():
    """Main function"""
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Check key tables
        check_sys_params(connection)
        check_ai_model_config(connection)
        
    except Error as e:
        print(f"Error during database operations: {e}")
    
    finally:
        if connection.is_connected():
            connection.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()