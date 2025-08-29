#!/usr/bin/env python3
"""
Check and update TTS EdgeTTS voice configuration in database
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
            print("Connected to database")
            return connection
    except Error as e:
        print(f"Connection error: {e}")
        return None

def check_tts_configurations(connection):
    """Check TTS configurations in database"""
    cursor = connection.cursor()
    
    print("=== TTS CONFIGURATION CHECK ===\n")
    
    # First, check available columns
    try:
        cursor.execute("DESCRIBE ai_model_config")
        columns = cursor.fetchall()
        config_columns = [col[0] for col in columns]
        print(f"Available ai_model_config columns: {config_columns}")
        
        # Use correct column names
        name_col = 'name' if 'name' in config_columns else ('model_name' if 'model_name' in config_columns else 'id')
        
        # 1. Check ai_model_config for TTS entries
        print("\n1. TTS Model Configurations:")
        cursor.execute(f"""
        SELECT id, model_type, {name_col}, config_json
        FROM ai_model_config 
        WHERE model_type = 'TTS'
        ORDER BY id
        """)
    except Error as e:
        print(f"Error checking columns: {e}")
        return []
    tts_configs = cursor.fetchall()
    
    edgetts_configs = []
    
    if tts_configs:
        for config in tts_configs:
            print(f"  ID: {config[0]}")
            print(f"  Name: {config[2]}")
            try:
                config_json = json.loads(config[3]) if config[3] else {}
                print(f"  Config: {json.dumps(config_json, indent=4)}")
                
                # Check if this is EdgeTTS and has voice config
                if config_json.get('type') == 'edge' or 'edge' in config[0].lower():
                    voice = config_json.get('voice', 'Not specified')
                    print(f"  >>> EdgeTTS Voice: {voice}")
                    if voice == 'en-GB-MaisieNeural':
                        print(f"  >>> NEEDS UPDATE: Found en-GB-MaisieNeural")
                        edgetts_configs.append({
                            'id': config[0],
                            'name': config[2],
                            'config': config_json,
                            'needs_update': True
                        })
                    elif voice == 'en-US-JennyNeural':
                        print(f"  >>> OK: Already using en-US-JennyNeural")
                        edgetts_configs.append({
                            'id': config[0],
                            'name': config[2],
                            'config': config_json,
                            'needs_update': False
                        })
                    else:
                        edgetts_configs.append({
                            'id': config[0],
                            'name': config[2],
                            'config': config_json,
                            'needs_update': False,
                            'current_voice': voice
                        })
                        
            except json.JSONDecodeError:
                print(f"  Config: {config[3]} (Invalid JSON)")
            print("  ---")
    else:
        print("  No TTS configurations found")
    
    # 2. Check ai_model_provider for TTS providers
    print("\n2. TTS Model Providers:")
    try:
        cursor.execute("DESCRIBE ai_model_provider")
        provider_columns = [col[0] for col in cursor.fetchall()]
        provider_name_col = 'name' if 'name' in provider_columns else ('provider_name' if 'provider_name' in provider_columns else 'id')
        
        cursor.execute(f"""
        SELECT id, provider_code, {provider_name_col}, fields
        FROM ai_model_provider 
        WHERE model_type = 'TTS'
        ORDER BY provider_code
        """)
    except Error as e:
        print(f"Error checking provider columns: {e}")
        cursor.execute("""
        SELECT id, provider_code, fields
        FROM ai_model_provider 
        WHERE model_type = 'TTS'
        ORDER BY provider_code
        """)
    tts_providers = cursor.fetchall()
    
    if tts_providers:
        for provider in tts_providers:
            print(f"  ID: {provider[0]}")
            print(f"  Code: {provider[1]}")
            if len(provider) > 2:
                print(f"  Name: {provider[2]}")
                fields_idx = 3
            else:
                fields_idx = 2
            
            if len(provider) > fields_idx:
                try:
                    fields = json.loads(provider[fields_idx]) if provider[fields_idx] else []
                    if fields:
                        print(f"  Fields: {json.dumps(fields, indent=4)}")
                    else:
                        print("  Fields: (none)")
                except:
                    print(f"  Fields: {provider[fields_idx]}")
            print("  ---")
    else:
        print("  No TTS providers found")
    
    # 3. Check agents and their TTS assignments
    print("\n3. Agent TTS Assignments:")
    cursor.execute("""
    SELECT a.id, a.agent_name, a.tts_model_id, a.tts_voice_id
    FROM ai_agent a
    WHERE a.tts_model_id IS NOT NULL OR a.tts_voice_id IS NOT NULL
    ORDER BY a.agent_name
    """)
    agent_tts = cursor.fetchall()
    
    if agent_tts:
        for agent in agent_tts:
            print(f"  Agent: {agent[1]} ({agent[0]})")
            print(f"    TTS Model: {agent[2] if agent[2] else 'Not set'}")
            print(f"    TTS Voice: {agent[3] if agent[3] else 'Not set'}")
            print("  ---")
    else:
        print("  No agents with TTS assignments found")
    
    cursor.close()
    return edgetts_configs

def update_edgetts_voice(connection, edgetts_configs):
    """Update EdgeTTS voice configurations"""
    cursor = connection.cursor()
    
    print("\n=== UPDATING EDGETTS VOICE ===\n")
    
    updates_made = 0
    
    for config_info in edgetts_configs:
        if config_info.get('needs_update', False):
            config_id = config_info['id']
            current_config = config_info['config']
            
            # Update the voice
            current_config['voice'] = 'en-US-JennyNeural'
            
            # Update in database
            try:
                cursor.execute("""
                UPDATE ai_model_config 
                SET config_json = %s 
                WHERE id = %s
                """, (json.dumps(current_config), config_id))
                
                print(f"[UPDATED] {config_id}: voice changed to en-US-JennyNeural")
                updates_made += 1
                
            except Error as e:
                print(f"[ERROR] Failed to update {config_id}: {e}")
    
    if updates_made > 0:
        try:
            connection.commit()
            print(f"\n[SUCCESS] {updates_made} TTS configurations updated successfully!")
        except Error as e:
            connection.rollback()
            print(f"\n[ERROR] Failed to commit changes: {e}")
    else:
        print("\n[INFO] No updates needed - all EdgeTTS configs already use correct voice")
    
    cursor.close()
    return updates_made

def main():
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Check current TTS configurations
        edgetts_configs = check_tts_configurations(connection)
        
        # Update if needed
        if edgetts_configs:
            needs_update = any(config.get('needs_update', False) for config in edgetts_configs)
            
            if needs_update:
                print("\n" + "="*50)
                print("Found EdgeTTS configurations that need updating!")
                print("="*50)
                
                response = input("Do you want to update them? (y/N): ").strip().lower()
                if response == 'y' or response == 'yes':
                    updates_made = update_edgetts_voice(connection, edgetts_configs)
                    
                    if updates_made > 0:
                        print("\n[NEXT STEPS]")
                        print("1. Restart the manager-api to reload configurations")
                        print("2. Test TTS with the new en-US-JennyNeural voice")
                else:
                    print("\nNo changes made.")
            else:
                print("\n[INFO] All EdgeTTS configurations are already using the correct voice!")
        else:
            print("\n[INFO] No EdgeTTS configurations found in database")
        
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main()