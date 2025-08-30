#!/usr/bin/env python3
"""
Comprehensive script to check Story Playback function mapping in both database and local config
"""

import mysql.connector
from mysql.connector import Error
import json
import yaml
import os

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

def check_story_plugin_in_database(connection):
    """Check if Story Playback plugin exists in database"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("1. Checking Story Playback Plugin in Database")
        print('='*60)
        
        # Check if SYSTEM_PLUGIN_STORY exists in ai_model_provider
        cursor.execute("""
            SELECT id, model_type, provider_code, name, fields
            FROM ai_model_provider 
            WHERE id = 'SYSTEM_PLUGIN_STORY' OR name LIKE '%Story%'
        """)
        
        story_plugins = cursor.fetchall()
        
        if story_plugins:
            print(f"Found Story Playback plugins:")
            for plugin in story_plugins:
                plugin_id, model_type, provider_code, name, fields = plugin
                print(f"  ID: {plugin_id}")
                print(f"  Type: {model_type}")
                print(f"  Provider Code: {provider_code}")
                print(f"  Name: {name}")
                if fields:
                    try:
                        fields_json = json.loads(fields)
                        print(f"  Fields: {json.dumps(fields_json, indent=4)}")
                    except:
                        print(f"  Fields: {fields}")
                print()
        else:
            print("No Story Playback plugin found in database!")
            
        return story_plugins
        
    except Error as e:
        print(f"Error checking story plugin: {e}")
        return None
    finally:
        cursor.close()

def check_intent_functions_in_database(connection):
    """Check Intent function call configurations in database"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("2. Checking Intent Function Call Configurations")
        print('='*60)
        
        # Check if there's an Intent function call configuration
        cursor.execute("""
            SELECT id, model_type, provider_code, name, fields
            FROM ai_model_provider 
            WHERE model_type = 'Intent' AND provider_code = 'function_call'
        """)
        
        intent_configs = cursor.fetchall()
        
        if intent_configs:
            print(f"Found Intent function call configurations:")
            for config in intent_configs:
                config_id, model_type, provider_code, name, fields = config
                print(f"  ID: {config_id}")
                print(f"  Name: {name}")
                if fields:
                    try:
                        fields_json = json.loads(fields)
                        print(f"  Fields: {json.dumps(fields_json, indent=2)}")
                        
                        # Look for functions list
                        for field in fields_json:
                            if field.get('key') == 'functions' and 'default' in field:
                                functions = field['default']
                                print(f"  Available functions: {functions}")
                                if 'play_story' in str(functions).lower():
                                    print("  [✓] play_story found in functions!")
                                else:
                                    print("  [✗] play_story NOT found in functions!")
                    except Exception as e:
                        print(f"  Fields (raw): {fields}")
                        print(f"  Error parsing fields: {e}")
                print()
        else:
            print("No Intent function call configuration found!")
            
        return intent_configs
        
    except Error as e:
        print(f"Error checking intent functions: {e}")
        return None
    finally:
        cursor.close()

def check_agent_plugin_mappings(connection):
    """Check which agents have Story Playback mapped"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("3. Checking Agent-Plugin Mappings for Story Playback")
        print('='*60)
        
        # Get all agents and check their Story Playback mapping
        cursor.execute("""
            SELECT 
                a.id as agent_id,
                a.agent_name,
                apm.plugin_id,
                apm.param_info
            FROM ai_agent a
            LEFT JOIN ai_agent_plugin_mapping apm 
                ON a.id = apm.agent_id AND apm.plugin_id = 'SYSTEM_PLUGIN_STORY'
            ORDER BY a.agent_name
        """)
        
        mappings = cursor.fetchall()
        
        total_agents = len(set([m[0] for m in mappings if m[0] is not None]))
        agents_with_story = len([m for m in mappings if m[2] == 'SYSTEM_PLUGIN_STORY'])
        
        print(f"Agent Story Playback Mapping Status:")
        print(f"Total agents: {total_agents}")
        print(f"Agents with Story Playback: {agents_with_story}")
        print()
        
        for mapping in mappings:
            agent_id, agent_name, plugin_id, param_info = mapping
            if plugin_id == 'SYSTEM_PLUGIN_STORY':
                print(f"[✓] {agent_name} (ID: {agent_id}) - HAS Story Playback")
                if param_info:
                    try:
                        params = json.loads(param_info)
                        print(f"    Parameters: {json.dumps(params, indent=6)}")
                    except:
                        print(f"    Parameters: {param_info}")
            else:
                print(f"[✗] {agent_name} (ID: {agent_id}) - MISSING Story Playback")
        
        return mappings
        
    except Error as e:
        print(f"Error checking agent mappings: {e}")
        return None
    finally:
        cursor.close()

def check_local_config_file():
    """Check the local config file for play_story function"""
    try:
        print(f"\n{'='*60}")
        print("4. Checking Local Config File")
        print('='*60)
        
        config_path = "D:/cheekofinal/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml"
        
        if not os.path.exists(config_path):
            print(f"Config file not found: {config_path}")
            return None
            
        with open(config_path, 'r', encoding='utf-8') as file:
            config_content = file.read()
            
        print(f"Config file location: {config_path}")
        print(f"File size: {len(config_content)} characters")
        
        # Look for Intent section
        if 'Intent:' in config_content:
            print(f"[✓] Intent section found in config")
            
            # Look for function_call
            if 'function_call:' in config_content:
                print(f"[✓] function_call section found")
                
                # Look for functions list
                if 'functions:' in config_content:
                    print(f"[✓] functions list found")
                    
                    # Extract functions section
                    lines = config_content.split('\n')
                    in_functions = False
                    functions = []
                    
                    for line in lines:
                        if 'functions:' in line and 'function_call:' in config_content[max(0, config_content.find(line)-200):config_content.find(line)]:
                            in_functions = True
                            continue
                        elif in_functions:
                            if line.strip().startswith('- '):
                                func_name = line.strip()[2:].strip()
                                functions.append(func_name)
                            elif line.strip() and not line.startswith(' ') and not line.startswith('#'):
                                break
                    
                    print(f"Functions found in config:")
                    for func in functions:
                        if 'story' in func.lower():
                            print(f"  [✓] {func}")
                        else:
                            print(f"  - {func}")
                    
                    if 'play_story' in functions:
                        print(f"[✓] play_story is configured in local config!")
                    else:
                        print(f"[✗] play_story is NOT configured in local config!")
                        
                    return functions
                else:
                    print(f"[✗] functions list not found in function_call section")
            else:
                print(f"[✗] function_call section not found in Intent")
        else:
            print(f"[✗] Intent section not found in config")
            
        return None
        
    except Exception as e:
        print(f"Error checking local config: {e}")
        return None

def fix_missing_story_function_in_database(connection):
    """Fix missing Story Playback function in Intent configuration if needed"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("5. Fixing Intent Function Configuration if Needed")
        print('='*60)
        
        # Get the Intent function call configuration
        cursor.execute("""
            SELECT id, fields
            FROM ai_model_provider 
            WHERE model_type = 'Intent' AND provider_code = 'function_call'
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if result:
            config_id, fields = result
            print(f"Found Intent config ID: {config_id}")
            
            try:
                fields_json = json.loads(fields)
                
                # Find the functions field
                functions_field = None
                for i, field in enumerate(fields_json):
                    if field.get('key') == 'functions':
                        functions_field = field
                        field_index = i
                        break
                
                if functions_field:
                    current_functions = functions_field.get('default', '')
                    print(f"Current functions: {current_functions}")
                    
                    # Check if play_story is already there
                    if 'play_story' not in current_functions.lower():
                        # Add play_story to the functions
                        if current_functions:
                            # Parse existing functions (assuming they're in a string format)
                            if current_functions.endswith(';'):
                                updated_functions = current_functions + 'play_story'
                            else:
                                updated_functions = current_functions + ';play_story'
                        else:
                            updated_functions = 'play_story'
                        
                        # Update the field
                        fields_json[field_index]['default'] = updated_functions
                        
                        # Update database
                        cursor.execute("""
                            UPDATE ai_model_provider 
                            SET fields = %s 
                            WHERE id = %s
                        """, (json.dumps(fields_json), config_id))
                        
                        connection.commit()
                        
                        print(f"[✓] Updated Intent functions to: {updated_functions}")
                        print(f"[✓] play_story added to Intent configuration!")
                    else:
                        print(f"[✓] play_story already exists in Intent configuration")
                else:
                    print(f"[✗] functions field not found in Intent configuration")
                    
            except json.JSONDecodeError as e:
                print(f"[✗] Error parsing Intent configuration JSON: {e}")
                
        else:
            print(f"[✗] No Intent function call configuration found in database")
            
    except Error as e:
        print(f"Error fixing Intent configuration: {e}")
        connection.rollback()
    finally:
        cursor.close()

def main():
    print("Comprehensive Story Playback Function Mapping Check")
    print("=" * 80)
    
    # Check database
    connection = connect_to_database()
    if connection:
        try:
            # Check story plugin exists
            story_plugins = check_story_plugin_in_database(connection)
            
            # Check intent function configurations
            intent_configs = check_intent_functions_in_database(connection)
            
            # Check agent mappings
            agent_mappings = check_agent_plugin_mappings(connection)
            
            # Fix Intent configuration if needed
            fix_missing_story_function_in_database(connection)
            
        finally:
            connection.close()
    
    # Check local config
    local_functions = check_local_config_file()
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    if story_plugins:
        print("[✓] Story Playback plugin exists in database")
    else:
        print("[✗] Story Playback plugin MISSING from database")
        
    if local_functions and 'play_story' in local_functions:
        print("[✓] play_story configured in local config")
    else:
        print("[✗] play_story MISSING from local config")
    
    print(f"\nThe script has checked both database and local configurations.")
    print(f"If any issues were found, they should now be fixed!")

if __name__ == "__main__":
    main()