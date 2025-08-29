#!/usr/bin/env python3
"""
Script to check what's in the Railway MySQL database
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

def check_tables(connection):
    """Check what tables exist in the database"""
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"\nFound {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")
    cursor.close()
    return [table[0] for table in tables]

def check_config_tables(connection):
    """Check configuration-related tables"""
    cursor = connection.cursor()
    
    # Check system parameters table
    print("\n=== System Parameters ===")
    try:
        cursor.execute("SELECT param_key, param_value FROM sys_params WHERE param_key LIKE '%log%' OR param_key LIKE '%config%'")
        params = cursor.fetchall()
        for param in params:
            print(f"  {param[0]}: {param[1]}")
    except Error as e:
        print(f"Error querying sys_params: {e}")
    
    # Check AI model configurations  
    print("\n=== AI Model Configurations ===")
    try:
        cursor.execute("SELECT id, model_type, name, config_json FROM ai_model_config WHERE model_type = 'LLM' LIMIT 5")
        models = cursor.fetchall()
        for model in models:
            print(f"  ID: {model[0]}")
            print(f"  Type: {model[1]}")
            print(f"  Name: {model[2]}")
            try:
                config = json.loads(model[3]) if model[3] else {}
                print(f"  Config: {json.dumps(config, indent=4)}")
            except:
                print(f"  Config: {model[3]}")
            print("  ---")
    except Error as e:
        print(f"Error querying ai_model_config: {e}")
    
    # Check server configurations
    print("\n=== Server Configurations ===")
    try:
        cursor.execute("SELECT * FROM server_config LIMIT 5")
        servers = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        for server in servers:
            server_dict = dict(zip(columns, server))
            print(f"  Server: {json.dumps(server_dict, indent=2, default=str)}")
    except Error as e:
        print(f"Error querying server_config: {e}")
    
    cursor.close()

def main():
    """Main function to check the database"""
    print("Connecting to Railway MySQL database...")
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        tables = check_tables(connection)
        check_config_tables(connection)
        
    except Error as e:
        print(f"Error during database operations: {e}")
    
    finally:
        if connection.is_connected():
            connection.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()