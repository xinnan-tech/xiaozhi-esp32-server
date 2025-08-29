#!/usr/bin/env python3
"""
Update EdgeTTS voice from en-GB-MaisieNeural to en-US-JennyNeural in database
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

def update_edge_tts_voice(connection):
    """Update EdgeTTS voice configuration"""
    cursor = connection.cursor()
    
    print("=== UPDATING EDGETTS VOICE ===\n")
    
    # 1. First, check the current TTS_EdgeTTS configuration
    cursor.execute("""
    SELECT id, model_name, config_json
    FROM ai_model_config 
    WHERE id = 'TTS_EdgeTTS'
    """)
    result = cursor.fetchone()
    
    if not result:
        print("[ERROR] TTS_EdgeTTS configuration not found!")
        return False
    
    config_id, model_name, config_json = result
    print(f"Found TTS EdgeTTS configuration: {config_id} - {model_name}")
    
    try:
        config = json.loads(config_json) if config_json else {}
        current_voice = config.get('voice', 'Not specified')
        print(f"Current voice: {current_voice}")
        
        if current_voice == 'en-US-JennyNeural':
            print("[INFO] Voice is already set to en-US-JennyNeural - no update needed!")
            return True
        elif current_voice == 'en-GB-MaisieNeural':
            print("[UPDATE] Changing voice from en-GB-MaisieNeural to en-US-JennyNeural")
            
            # Update the voice
            config['voice'] = 'en-US-JennyNeural'
            
            # Update in database
            cursor.execute("""
            UPDATE ai_model_config 
            SET config_json = %s 
            WHERE id = %s
            """, (json.dumps(config), config_id))
            
            connection.commit()
            print("[SUCCESS] EdgeTTS voice updated successfully!")
            return True
        else:
            print(f"[INFO] Current voice is '{current_voice}' - updating to en-US-JennyNeural")
            config['voice'] = 'en-US-JennyNeural'
            
            cursor.execute("""
            UPDATE ai_model_config 
            SET config_json = %s 
            WHERE id = %s
            """, (json.dumps(config), config_id))
            
            connection.commit()
            print("[SUCCESS] EdgeTTS voice updated successfully!")
            return True
            
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in config: {e}")
        return False
    except Error as e:
        print(f"[ERROR] Database update failed: {e}")
        connection.rollback()
        return False
    
    finally:
        cursor.close()

def verify_update(connection):
    """Verify the update was successful"""
    cursor = connection.cursor()
    
    print("\n=== VERIFICATION ===")
    cursor.execute("""
    SELECT config_json
    FROM ai_model_config 
    WHERE id = 'TTS_EdgeTTS'
    """)
    result = cursor.fetchone()
    
    if result:
        try:
            config = json.loads(result[0])
            voice = config.get('voice', 'Not found')
            print(f"Updated voice setting: {voice}")
            
            if voice == 'en-US-JennyNeural':
                print("[VERIFIED] Voice successfully updated to en-US-JennyNeural!")
                return True
            else:
                print(f"[ERROR] Voice is still '{voice}' - update may have failed")
                return False
        except:
            print("[ERROR] Could not parse updated configuration")
            return False
    else:
        print("[ERROR] Could not find TTS_EdgeTTS configuration for verification")
        return False
    
    cursor.close()

def main():
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Update the configuration
        success = update_edge_tts_voice(connection)
        
        if success:
            # Verify the update
            verified = verify_update(connection)
            
            if verified:
                print("\n[COMPLETE] EdgeTTS voice has been successfully updated!")
                print("\nNext steps:")
                print("1. Restart the manager-api to reload the configuration")
                print("2. Test TTS functionality with the new en-US-JennyNeural voice")
                print("3. The xiaozhi-server should now use the updated voice from the database")
            else:
                print("\n[WARNING] Update completed but verification failed")
        else:
            print("\n[FAILED] Could not update EdgeTTS voice configuration")
        
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main()