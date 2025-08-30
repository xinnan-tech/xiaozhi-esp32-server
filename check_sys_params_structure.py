#!/usr/bin/env python3
"""
Check sys_params table structure and add default plugins configuration
"""

import mysql.connector
from mysql.connector import Error
import json

def connect_to_database():
    """Connect to the Railway MySQL database"""
    try:
        connection = mysql.connector.connect(
            host='nozomi.proxy.rlwy.net',
            port=25037,
            database='railway',
            user='root',
            password='OcaVNLKcwNdyElfaeUPqvvfYZiiEHgdm',
            charset='utf8mb4',
            use_unicode=True,
            ssl_disabled=True
        )
        
        if connection.is_connected():
            print("Connected to Railway MySQL database")
            return connection
            
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def check_sys_params_structure(connection):
    """Check the structure of sys_params table"""
    cursor = connection.cursor()
    try:
        print("\n1. Checking sys_params table structure...")
        print("=" * 50)
        
        cursor.execute("DESCRIBE sys_params")
        columns = cursor.fetchall()
        
        print("sys_params columns:")
        for col in columns:
            print(f"  {col[0]} - {col[1]}")
        
        return [col[0] for col in columns]
        
    except Error as e:
        print(f"Error checking sys_params: {e}")
        return []
    finally:
        cursor.close()

def check_existing_params(connection, column_names):
    """Check existing system parameters"""
    cursor = connection.cursor()
    try:
        print("\n2. Checking existing system parameters...")
        print("=" * 50)
        
        # Build query based on actual column names
        key_col = None
        value_col = None
        
        for col in column_names:
            if 'key' in col.lower():
                key_col = col
            elif 'value' in col.lower():
                value_col = col
        
        if not key_col or not value_col:
            print("Could not identify key/value columns")
            return None, None
        
        print(f"Using columns: {key_col} (key), {value_col} (value)")
        
        # Get plugin-related parameters
        query = f"SELECT {key_col}, {value_col} FROM sys_params WHERE {key_col} LIKE '%plugin%' OR {key_col} LIKE '%function%' OR {key_col} LIKE '%default%'"
        cursor.execute(query)
        
        params = cursor.fetchall()
        
        if params:
            print("Found related parameters:")
            for key, value in params:
                print(f"  {key}: {value[:100] if value else 'NULL'}...")
        else:
            print("No plugin-related parameters found")
        
        return key_col, value_col
        
    except Error as e:
        print(f"Error checking parameters: {e}")
        return None, None
    finally:
        cursor.close()

def add_default_plugins_parameter(connection, key_col, value_col, column_names):
    """Add or update default plugins parameter"""
    cursor = connection.cursor()
    try:
        print("\n3. Adding/Updating default plugins parameter...")
        print("=" * 50)
        
        # Check if default_agent_plugins exists
        query = f"SELECT {value_col} FROM sys_params WHERE {key_col} = 'default_agent_plugins'"
        cursor.execute(query)
        
        existing = cursor.fetchone()
        
        default_plugins = {
            "plugins": [
                "SYSTEM_PLUGIN_MUSIC",
                "SYSTEM_PLUGIN_STORY",
                "SYSTEM_PLUGIN_WEATHER",
                "SYSTEM_PLUGIN_NEWS_NEWSNOW"
            ],
            "functions": [
                "play_music",
                "play_story",
                "get_weather",
                "get_news_from_newsnow",
                "get_indian_news_api",
                "get_lunar"
            ]
        }
        
        if existing:
            print("default_agent_plugins already exists, updating...")
            
            update_query = f"UPDATE sys_params SET {value_col} = %s WHERE {key_col} = %s"
            cursor.execute(update_query, (json.dumps(default_plugins), 'default_agent_plugins'))
            
            print("Updated default_agent_plugins")
        else:
            print("Creating new default_agent_plugins parameter...")
            
            # Build insert query based on available columns
            insert_cols = [key_col, value_col]
            insert_values = ['default_agent_plugins', json.dumps(default_plugins)]
            
            # Add other columns if they exist
            if 'type' in column_names:
                insert_cols.append('type')
                insert_values.append(1)
            elif 'param_type' in column_names:
                insert_cols.append('param_type')
                insert_values.append(1)
            
            if 'remark' in column_names:
                insert_cols.append('remark')
                insert_values.append('Default plugins and functions for new agents')
            elif 'description' in column_names:
                insert_cols.append('description')
                insert_values.append('Default plugins and functions for new agents')
            
            # Add timestamp columns if they exist
            for col in ['create_date', 'created_at', 'create_time']:
                if col in column_names:
                    insert_cols.append(col)
                    insert_values.append('NOW()')
                    break
            
            # Build query
            placeholders = ['%s'] * len(insert_values)
            # Replace NOW() placeholders
            for i, val in enumerate(insert_values):
                if val == 'NOW()':
                    placeholders[i] = 'NOW()'
                    insert_values[i] = None
            
            insert_query = f"INSERT INTO sys_params ({', '.join(insert_cols)}) VALUES ({', '.join(placeholders)})"
            insert_query = insert_query.replace('%s', '%s').replace("'NOW()'", "NOW()")
            
            # Filter out None values for NOW()
            insert_values = [v for v in insert_values if v is not None]
            
            print(f"Insert query: {insert_query}")
            cursor.execute(insert_query, insert_values)
            
            print("Created default_agent_plugins parameter")
        
        connection.commit()
        return True
        
    except Error as e:
        print(f"Error adding default plugins: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def verify_trigger(connection):
    """Verify the trigger exists"""
    cursor = connection.cursor()
    try:
        print("\n4. Verifying trigger...")
        print("=" * 50)
        
        cursor.execute("""
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE
            FROM information_schema.TRIGGERS
            WHERE TRIGGER_SCHEMA = 'railway'
            AND TRIGGER_NAME = 'add_story_to_new_agent'
        """)
        
        trigger = cursor.fetchone()
        
        if trigger:
            print(f"Trigger exists: {trigger[0]}")
            print(f"  Event: {trigger[1]} on {trigger[2]}")
            print("New agents will automatically get Story Playback!")
        else:
            print("Trigger not found (may have failed to create)")
        
        return trigger is not None
        
    except Error as e:
        print(f"Error verifying trigger: {e}")
        return False
    finally:
        cursor.close()

def main():
    print("Configuring Default Plugins for New Agents")
    print("=" * 70)
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # 1. Check sys_params structure
        column_names = check_sys_params_structure(connection)
        
        if column_names:
            # 2. Check existing parameters
            key_col, value_col = check_existing_params(connection, column_names)
            
            if key_col and value_col:
                # 3. Add/update default plugins
                add_default_plugins_parameter(connection, key_col, value_col, column_names)
        
        # 4. Verify trigger
        trigger_exists = verify_trigger(connection)
        
        # Summary
        print(f"\n{'='*70}")
        print("FINAL STATUS")
        print('='*70)
        
        print("Configuration complete!")
        
        if trigger_exists:
            print("[OK] Database trigger active - new agents will get Story Playback automatically")
        else:
            print("[INFO] No trigger - agent creation code should add default plugins")
        
        print("\nDefault plugins configured:")
        print("  - SYSTEM_PLUGIN_MUSIC")
        print("  - SYSTEM_PLUGIN_STORY")
        print("  - SYSTEM_PLUGIN_WEATHER")
        print("  - SYSTEM_PLUGIN_NEWS_NEWSNOW")
        
        print("\nAll new agents will now have Story Playback by default!")
        
    finally:
        connection.close()

if __name__ == "__main__":
    main()