#!/usr/bin/env python3
"""
Fix Intent function configuration to include play_story
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

def check_and_fix_intent_config(connection):
    """Check and fix Intent function configuration"""
    cursor = connection.cursor()
    try:
        # Get current Intent configuration
        cursor.execute("""
            SELECT id, fields
            FROM ai_model_provider 
            WHERE model_type = 'Intent' AND provider_code = 'function_call'
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            print("ERROR: Intent function call configuration not found!")
            return False
        
        config_id, fields = result
        print(f"Found Intent config: {config_id}")
        
        try:
            fields_json = json.loads(fields)
            print(f"Current fields count: {len(fields_json)}")
            
            # Check if functions field exists
            functions_field_exists = False
            for field in fields_json:
                if field.get('key') == 'functions':
                    functions_field_exists = True
                    current_functions = field.get('default', '')
                    print(f"Current functions: {current_functions}")
                    
                    if 'play_story' in current_functions.lower():
                        print("play_story already exists in functions!")
                        return True
                    break
            
            if not functions_field_exists:
                print("Functions field missing! Adding it...")
                
                # Add functions field with all necessary functions
                functions_field = {
                    "key": "functions",
                    "type": "array", 
                    "label": "Functions",
                    "default": "play_music;play_story;get_weather;get_indian_news_api;get_news_from_newsnow;get_lunar"
                }
                
                fields_json.append(functions_field)
            else:
                print("Adding play_story to existing functions...")
                for i, field in enumerate(fields_json):
                    if field.get('key') == 'functions':
                        current_functions = field.get('default', '')
                        if current_functions and not current_functions.endswith(';'):
                            updated_functions = current_functions + ';play_story'
                        elif current_functions:
                            updated_functions = current_functions + 'play_story'
                        else:
                            updated_functions = 'play_story;play_music;get_weather;get_indian_news_api;get_news_from_newsnow;get_lunar'
                        
                        fields_json[i]['default'] = updated_functions
                        print(f"Updated functions to: {updated_functions}")
                        break
            
            # Update database
            cursor.execute("""
                UPDATE ai_model_provider 
                SET fields = %s 
                WHERE id = %s
            """, (json.dumps(fields_json), config_id))
            
            connection.commit()
            print("SUCCESS: Intent configuration updated!")
            return True
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return False
            
    except Error as e:
        print(f"Database error: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def add_story_to_missing_agents(connection):
    """Add Story Playback to agents that don't have it"""
    cursor = connection.cursor()
    try:
        # Get agents without Story Playback
        cursor.execute("""
            SELECT a.id, a.agent_name
            FROM ai_agent a
            LEFT JOIN ai_agent_plugin_mapping apm 
                ON a.id = apm.agent_id AND apm.plugin_id = 'SYSTEM_PLUGIN_STORY'
            WHERE apm.plugin_id IS NULL
        """)
        
        missing_agents = cursor.fetchall()
        
        if not missing_agents:
            print("All agents already have Story Playback!")
            return True
        
        print(f"Adding Story Playback to {len(missing_agents)} agents...")
        
        # Default Story Playback parameters
        param_info = {
            "story_dir": "./stories",
            "story_ext": ".mp3;.wav;.m4a",
            "refresh_time": "300"
        }
        
        success_count = 0
        for agent_id, agent_name in missing_agents:
            try:
                cursor.execute("""
                    INSERT INTO ai_agent_plugin_mapping 
                    (agent_id, plugin_id, param_info)
                    VALUES (%s, %s, %s)
                """, (agent_id, "SYSTEM_PLUGIN_STORY", json.dumps(param_info)))
                
                print(f"Added Story Playback to: {agent_name}")
                success_count += 1
                
            except Error as e:
                print(f"Failed to add to {agent_name}: {e}")
        
        connection.commit()
        print(f"SUCCESS: Added Story Playback to {success_count} agents!")
        return True
        
    except Error as e:
        print(f"Error adding Story Playback to agents: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def verify_final_state(connection):
    """Verify everything is working"""
    cursor = connection.cursor()
    try:
        # Check Intent functions
        cursor.execute("""
            SELECT fields
            FROM ai_model_provider 
            WHERE model_type = 'Intent' AND provider_code = 'function_call'
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if result:
            fields_json = json.loads(result[0])
            for field in fields_json:
                if field.get('key') == 'functions':
                    functions = field.get('default', '')
                    print(f"Final Intent functions: {functions}")
                    break
        
        # Check agent count
        cursor.execute("""
            SELECT 
                COUNT(*) as total_agents,
                SUM(CASE WHEN apm.plugin_id IS NOT NULL THEN 1 ELSE 0 END) as agents_with_story
            FROM ai_agent a
            LEFT JOIN ai_agent_plugin_mapping apm 
                ON a.id = apm.agent_id AND apm.plugin_id = 'SYSTEM_PLUGIN_STORY'
        """)
        
        total, with_story = cursor.fetchone()
        print(f"Final state: {with_story}/{total} agents have Story Playback")
        
        if with_story == total:
            print("SUCCESS: All agents now have Story Playback!")
            return True
        else:
            print(f"WARNING: {total - with_story} agents still missing Story Playback")
            return False
        
    except Error as e:
        print(f"Error verifying final state: {e}")
        return False
    finally:
        cursor.close()

def main():
    print("Fixing Story Playback Function Configuration")
    print("=" * 50)
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # 1. Fix Intent configuration
        print("\n1. Fixing Intent Function Configuration...")
        intent_fixed = check_and_fix_intent_config(connection)
        
        # 2. Add Story Playback to missing agents
        print("\n2. Adding Story Playback to Missing Agents...")
        agents_fixed = add_story_to_missing_agents(connection)
        
        # 3. Verify final state
        print("\n3. Verifying Final State...")
        final_ok = verify_final_state(connection)
        
        # Summary
        print(f"\n{'='*50}")
        print("FINAL RESULT")
        print('='*50)
        
        if intent_fixed:
            print("Intent configuration: FIXED")
        else:
            print("Intent configuration: FAILED")
            
        if agents_fixed:
            print("Agent mappings: FIXED") 
        else:
            print("Agent mappings: FAILED")
            
        if final_ok:
            print("Overall status: SUCCESS - Story Playback ready!")
        else:
            print("Overall status: PARTIAL - Some issues remain")
        
    finally:
        connection.close()

if __name__ == "__main__":
    main()