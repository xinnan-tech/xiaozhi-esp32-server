#!/usr/bin/env python3
"""
Simple script to check and fix Story Playback function mapping
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
            print("Successfully connected to Railway MySQL database")
            return connection
            
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def check_story_plugin_exists(connection):
    """Check if Story Playback plugin exists"""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, provider_code, name
            FROM ai_model_provider 
            WHERE id = 'SYSTEM_PLUGIN_STORY'
        """)
        
        result = cursor.fetchone()
        if result:
            plugin_id, provider_code, name = result
            print(f"[OK] Story Playback plugin exists: {plugin_id}")
            print(f"     Provider code: {provider_code}")
            return True
        else:
            print(f"[ERROR] Story Playback plugin not found!")
            return False
            
    except Error as e:
        print(f"Error checking story plugin: {e}")
        return False
    finally:
        cursor.close()

def check_intent_function_configuration(connection):
    """Check Intent function call configuration"""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, fields
            FROM ai_model_provider 
            WHERE model_type = 'Intent' AND provider_code = 'function_call'
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if result:
            config_id, fields = result
            print(f"[OK] Intent function call config found: {config_id}")
            
            try:
                fields_json = json.loads(fields)
                
                # Find functions field
                functions_value = None
                for field in fields_json:
                    if field.get('key') == 'functions':
                        functions_value = field.get('default', '')
                        break
                
                if functions_value:
                    print(f"Current functions: {functions_value}")
                    
                    if 'play_story' in functions_value.lower():
                        print("[OK] play_story found in Intent functions!")
                        return True, config_id, fields_json
                    else:
                        print("[MISSING] play_story NOT found in Intent functions!")
                        return False, config_id, fields_json
                else:
                    print("[ERROR] No functions field found in Intent config!")
                    return False, config_id, None
                    
            except json.JSONDecodeError:
                print("[ERROR] Could not parse Intent configuration JSON")
                return False, config_id, None
                
        else:
            print("[ERROR] Intent function call configuration not found!")
            return False, None, None
            
    except Error as e:
        print(f"Error checking Intent config: {e}")
        return False, None, None
    finally:
        cursor.close()

def fix_intent_functions(connection, config_id, fields_json):
    """Add play_story to Intent functions if missing"""
    cursor = connection.cursor()
    try:
        # Find and update the functions field
        for i, field in enumerate(fields_json):
            if field.get('key') == 'functions':
                current_functions = field.get('default', '')
                
                # Add play_story if not present
                if current_functions and not current_functions.endswith(';'):
                    updated_functions = current_functions + ';play_story'
                elif current_functions:
                    updated_functions = current_functions + 'play_story'
                else:
                    updated_functions = 'play_story'
                
                fields_json[i]['default'] = updated_functions
                break
        
        # Update database
        cursor.execute("""
            UPDATE ai_model_provider 
            SET fields = %s 
            WHERE id = %s
        """, (json.dumps(fields_json), config_id))
        
        connection.commit()
        
        print(f"[FIXED] Added play_story to Intent functions!")
        print(f"Updated functions: {updated_functions}")
        return True
        
    except Error as e:
        print(f"Error fixing Intent functions: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def check_agent_story_mappings(connection):
    """Check which agents have Story Playback"""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT 
                a.id,
                a.agent_name,
                CASE WHEN apm.plugin_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_story
            FROM ai_agent a
            LEFT JOIN ai_agent_plugin_mapping apm 
                ON a.id = apm.agent_id AND apm.plugin_id = 'SYSTEM_PLUGIN_STORY'
            ORDER BY a.agent_name
        """)
        
        results = cursor.fetchall()
        
        total = len(results)
        with_story = len([r for r in results if r[2] == 'YES'])
        
        print(f"\nAgent Story Playback Status:")
        print(f"Total agents: {total}")
        print(f"With Story Playback: {with_story}")
        
        if with_story < total:
            print(f"Missing Story Playback:")
            for agent_id, agent_name, has_story in results:
                if has_story == 'NO':
                    print(f"  - {agent_name} (ID: {agent_id})")
        else:
            print("[OK] All agents have Story Playback!")
            
        return with_story == total
        
    except Error as e:
        print(f"Error checking agent mappings: {e}")
        return False
    finally:
        cursor.close()

def main():
    print("Story Playback Function Check")
    print("=" * 50)
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # 1. Check if Story plugin exists
        print("\n1. Checking Story Playback Plugin...")
        story_exists = check_story_plugin_exists(connection)
        
        # 2. Check Intent function configuration
        print("\n2. Checking Intent Function Configuration...")
        has_play_story, config_id, fields_json = check_intent_function_configuration(connection)
        
        # 3. Fix Intent functions if needed
        if not has_play_story and config_id and fields_json:
            print("\n3. Fixing Intent Function Configuration...")
            fix_intent_functions(connection, config_id, fields_json)
        elif has_play_story:
            print("\n3. Intent Configuration - OK, no fix needed")
        
        # 4. Check agent mappings
        print("\n4. Checking Agent Story Playback Mappings...")
        all_agents_have_story = check_agent_story_mappings(connection)
        
        # Summary
        print(f"\n{'='*50}")
        print("SUMMARY")
        print('='*50)
        
        if story_exists:
            print("[✓] Story Playback plugin exists in database")
        else:
            print("[✗] Story Playback plugin missing")
            
        if has_play_story:
            print("[✓] play_story configured in Intent functions")
        else:
            print("[✗] play_story missing from Intent functions")
            
        if all_agents_have_story:
            print("[✓] All agents have Story Playback mapped")
        else:
            print("[✗] Some agents missing Story Playback")
        
    finally:
        connection.close()

if __name__ == "__main__":
    main()