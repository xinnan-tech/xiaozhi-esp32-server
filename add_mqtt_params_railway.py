#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to add MQTT configuration parameters to Railway MySQL database
"""

import pymysql
import sys
import io
from typing import Optional

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Railway MySQL Database configuration
DB_CONFIG = {
    'host': 'nozomi.proxy.rlwy.net',
    'port': 25037,
    'user': 'root',
    'password': 'OcaVNLKcwNdyElfaeUPqvvfYZiiEHgdm',
    'database': 'railway',
    'charset': 'utf8mb4'
}

# MQTT parameters to add
MQTT_PARAMS = [
    {
        'id': 120,
        'param_code': 'mqtt.broker',
        'param_value': '192.168.1.107',
        'value_type': 'string',
        'param_type': 1,
        'remark': 'MQTT broker IP address'
    },
    {
        'id': 121,
        'param_code': 'mqtt.port',
        'param_value': '1883',
        'value_type': 'string',
        'param_type': 1,
        'remark': 'MQTT broker port'
    },
    {
        'id': 122,
        'param_code': 'mqtt.signature_key',
        'param_value': 'test-signature-key-12345',
        'value_type': 'string',
        'param_type': 1,
        'remark': 'MQTT signature key for authentication'
    }
]

def connect_to_db():
    """Connect to the Railway MySQL database"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print(f"✅ Connected to Railway MySQL database")
        return connection
    except pymysql.Error as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def check_existing_params(cursor, param_code: str) -> Optional[dict]:
    """Check if a parameter already exists"""
    query = "SELECT * FROM sys_params WHERE param_code = %s"
    cursor.execute(query, (param_code,))
    result = cursor.fetchone()
    return result

def get_next_available_id(cursor) -> int:
    """Get the next available ID for sys_params table"""
    query = "SELECT MAX(id) as max_id FROM sys_params"
    cursor.execute(query)
    result = cursor.fetchone()
    if result and result['max_id']:
        return result['max_id'] + 1
    return 120  # Start from 120 if table is empty

def insert_or_update_param(cursor, param: dict) -> bool:
    """Insert a new parameter or update existing one"""
    try:
        # First check if it already exists
        existing = check_existing_params(cursor, param['param_code'])
        if existing:
            print(f"⚠️  Parameter '{param['param_code']}' already exists with value: {existing['param_value']}")
            
            # Update the existing parameter
            update_query = """
                UPDATE sys_params 
                SET param_value = %s, remark = %s 
                WHERE param_code = %s
            """
            cursor.execute(update_query, (param['param_value'], param['remark'], param['param_code']))
            print(f"   ✅ Updated parameter '{param['param_code']}' to: {param['param_value']}")
            return True
        
        # Get next available ID if the specified one is taken
        check_id_query = "SELECT id FROM sys_params WHERE id = %s"
        cursor.execute(check_id_query, (param['id'],))
        if cursor.fetchone():
            param['id'] = get_next_available_id(cursor)
            print(f"   ℹ️  Using ID {param['id']} for '{param['param_code']}'")
        
        # Insert new parameter
        insert_query = """
            INSERT INTO sys_params (id, param_code, param_value, value_type, param_type, remark)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            param['id'],
            param['param_code'],
            param['param_value'],
            param['value_type'],
            param['param_type'],
            param['remark']
        ))
        print(f"✅ Added parameter '{param['param_code']}' with value: {param['param_value']}")
        return True
    except pymysql.Error as e:
        print(f"❌ Failed to insert/update '{param['param_code']}': {e}")
        return False

def verify_params(cursor):
    """Verify that all MQTT parameters are in the database"""
    print("\n📋 Current MQTT parameters in database:")
    print("-" * 50)
    query = "SELECT param_code, param_value, remark FROM sys_params WHERE param_code LIKE 'mqtt.%' ORDER BY param_code"
    cursor.execute(query)
    results = cursor.fetchall()
    
    if results:
        for row in results:
            print(f"   • {row['param_code']}: {row['param_value']}")
            print(f"     ({row['remark']})")
    else:
        print("   No MQTT parameters found")
    
    return len(results) > 0

def main():
    print("🔧 Railway MySQL - MQTT Parameter Configuration Tool")
    print("=" * 60)
    print(f"📍 Connecting to: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"📦 Database: {DB_CONFIG['database']}")
    print("=" * 60)
    
    # Connect to database
    connection = connect_to_db()
    
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            print("\n📝 Adding/Updating MQTT parameters...")
            print("-" * 50)
            
            # Add each parameter
            changes_made = False
            for param in MQTT_PARAMS:
                if insert_or_update_param(cursor, param):
                    changes_made = True
            
            # Commit changes
            if changes_made:
                connection.commit()
                print("\n✅ All changes committed to database")
            else:
                print("\n⚠️  No changes were made")
            
            # Verify parameters
            verify_params(cursor)
            
            print("\n" + "=" * 60)
            print("✅ MQTT parameters configuration complete!")
            print("\n⚠️  IMPORTANT NEXT STEPS:")
            print("   1. Restart the manager-api server for changes to take effect")
            print("   2. The ESP32 device should now receive MQTT configuration")
            print("   3. The Python client should also connect successfully")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        connection.rollback()
    finally:
        connection.close()
        print("\n🔌 Database connection closed")

if __name__ == "__main__":
    print("\n🚀 This script will configure MQTT parameters in your Railway MySQL database")
    print("   The following parameters will be added/updated:")
    print("   • mqtt.broker: 139.59.7.72")
    print("   • mqtt.port: 1883")
    print("   • mqtt.signature_key: test-signature-key-12345\n")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")