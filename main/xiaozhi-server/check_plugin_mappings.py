#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to check plugin mappings and agent configurations in the database
This will help us understand how play_music is configured and what's needed for play_story
"""
import mysql.connector
import json
import sys
from mysql.connector import Error

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import os
    os.system("chcp 65001 >nul 2>&1")

def safe_print(text):
    """Safely print text with UTF-8 encoding"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('utf-8', errors='replace').decode('utf-8'))

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

def check_plugin_providers(connection):
    """Check available plugin providers"""
    cursor = connection.cursor()
    print("\n=== Plugin Providers ===")
    try:
        cursor.execute("""
        SELECT id, provider_code, name, fields, sort 
        FROM ai_model_provider 
        WHERE model_type = 'Plugin' 
        ORDER BY sort
        """)
        providers = cursor.fetchall()
        
        print(f"Found {len(providers)} plugin providers:")
        for provider in providers:
            safe_print(f"  ID: {provider[0]}")
            safe_print(f"  Code: {provider[1]}")
            safe_print(f"  Name: {provider[2]}")
            safe_print(f"  Sort: {provider[4]}")
            try:
                fields = json.loads(provider[3]) if provider[3] else []
                if fields:
                    safe_print(f"  Fields: {json.dumps(fields, indent=4)}")
                else:
                    safe_print("  Fields: (none)")
            except:
                safe_print(f"  Fields: {provider[3]}")
            safe_print("  ---")
    except Error as e:
        print(f"Error querying plugin providers: {e}")
    cursor.close()

def check_function_call_config(connection):
    """Check function_call intent configuration"""
    cursor = connection.cursor()
    print("\n=== Function Call Configuration ===")
    try:
        cursor.execute("""
        SELECT id, name, config_json, remark 
        FROM ai_model_config 
        WHERE id = 'Intent_function_call'
        """)
        result = cursor.fetchone()
        
        if result:
            print(f"ID: {result[0]}")
            print(f"Name: {result[1]}")
            try:
                config = json.loads(result[2]) if result[2] else {}
                print(f"Config: {json.dumps(config, indent=2)}")
            except:
                print(f"Config: {result[2]}")
            print(f"Remark: {result[3]}")
        else:
            print("No function_call configuration found!")
    except Error as e:
        print(f"Error querying function_call config: {e}")
    cursor.close()

def check_agents(connection):
    """Check available agents"""
    cursor = connection.cursor()
    print("\n=== Available Agents ===")
    try:
        cursor.execute("""
        SELECT id, name, intent_provider, creator, create_date 
        FROM ai_agent 
        ORDER BY create_date DESC 
        LIMIT 10
        """)
        agents = cursor.fetchall()
        
        print(f"Found {len(agents)} recent agents:")
        for agent in agents:
            print(f"  ID: {agent[0]}")
            print(f"  Name: {agent[1]}")
            print(f"  Intent Provider: {agent[2]}")
            print(f"  Creator: {agent[3]}")
            print(f"  Created: {agent[4]}")
            print("  ---")
    except Error as e:
        print(f"Error querying agents: {e}")
    cursor.close()
    return agents

def check_plugin_mappings(connection, agents):
    """Check plugin mappings for agents"""
    cursor = connection.cursor()
    print("\n=== Agent Plugin Mappings ===")
    
    for agent in agents:
        agent_id = agent[0]
        agent_name = agent[1]
        
        print(f"\nAgent: {agent_name} ({agent_id})")
        try:
            cursor.execute("""
            SELECT m.plugin_id, p.provider_code, p.name, m.param_info
            FROM ai_agent_plugin_mapping m
            JOIN ai_model_provider p ON p.id = m.plugin_id
            WHERE m.agent_id = %s
            ORDER BY p.sort
            """, (agent_id,))
            mappings = cursor.fetchall()
            
            if mappings:
                print(f"  Plugins ({len(mappings)}):")
                for mapping in mappings:
                    print(f"    - {mapping[1]} ({mapping[2]})")
                    if mapping[3]:
                        try:
                            params = json.loads(mapping[3])
                            if params:
                                print(f"      Params: {json.dumps(params, indent=6)}")
                        except:
                            print(f"      Params: {mapping[3]}")
            else:
                print("  No plugin mappings found")
        except Error as e:
            print(f"  Error querying plugin mappings for {agent_name}: {e}")
    
    cursor.close()

def check_play_story_status(connection):
    """Check if play_story plugin exists"""
    cursor = connection.cursor()
    print("\n=== Play Story Status Check ===")
    
    # Check if play_story provider exists
    try:
        cursor.execute("""
        SELECT id, provider_code, name 
        FROM ai_model_provider 
        WHERE provider_code = 'play_story' OR id LIKE '%STORY%'
        """)
        story_providers = cursor.fetchall()
        
        if story_providers:
            print("✓ Play Story provider found:")
            for provider in story_providers:
                print(f"  - {provider[0]}: {provider[1]} ({provider[2]})")
        else:
            print("✗ Play Story provider NOT found")
    except Error as e:
        print(f"Error checking play_story provider: {e}")
    
    # Check if any agents have play_story mapped
    try:
        cursor.execute("""
        SELECT a.name, a.id, m.plugin_id
        FROM ai_agent a
        JOIN ai_agent_plugin_mapping m ON a.id = m.agent_id
        JOIN ai_model_provider p ON p.id = m.plugin_id
        WHERE p.provider_code = 'play_story'
        """)
        story_mappings = cursor.fetchall()
        
        if story_mappings:
            print("✓ Agents with play_story mapping:")
            for mapping in story_mappings:
                print(f"  - {mapping[0]} ({mapping[1]})")
        else:
            print("✗ No agents have play_story mapping")
    except Error as e:
        print(f"Error checking play_story mappings: {e}")
    
    cursor.close()

def generate_sql_script():
    """Generate the SQL script to add play_story support"""
    timestamp = "202508291600"  # Current timestamp
    
    sql_content = f"""-- Add play_story plugin support to all agents
-- Generated automatically to match the pattern of existing plugins like play_music

-- 1. Add play_story plugin provider (if not exists)
DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_PLUGIN_STORY';
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields, sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_STORY', 'Plugin', 'play_story', '服务器故事播放', JSON_ARRAY(), 25, 0, NOW(), 0, NOW());

-- 2. Add play_story plugin to all existing agents that have play_music
-- This ensures consistency - if an agent can play music, it should also be able to play stories
INSERT INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
SELECT DISTINCT m.agent_id, 'SYSTEM_PLUGIN_STORY', '{{}}'
FROM ai_agent_plugin_mapping m
JOIN ai_model_provider p ON p.id = m.plugin_id
WHERE p.provider_code = 'play_music'
  AND NOT EXISTS (
    SELECT 1 FROM ai_agent_plugin_mapping m2
    JOIN ai_model_provider p2 ON p2.id = m2.plugin_id
    WHERE m2.agent_id = m.agent_id AND p2.provider_code = 'play_story'
  );

-- 3. Update documentation
UPDATE `ai_model_provider` SET 
`fields` = JSON_ARRAY(
    JSON_OBJECT('key', 'story_dir', 'type', 'string', 'label', '故事文件存放路径', 'default', './stories'),
    JSON_OBJECT('key', 'story_ext', 'type', 'array', 'label', '故事文件类型', 'default', '.mp3;.wav;.p3'),
    JSON_OBJECT('key', 'refresh_time', 'type', 'number', 'label', '故事列表刷新间隔(秒)', 'default', '300')
)
WHERE id = 'SYSTEM_PLUGIN_STORY';
"""
    
    # Write SQL file
    sql_file_path = f"d:\\cheekofinal\\xiaozhi-esp32-server\\main\\manager-api\\src\\main\\resources\\db\\changelog\\{timestamp}_add_play_story.sql"
    with open(sql_file_path, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    # Generate changelog entry
    changelog_entry = f"""  - changeSet:
      id: {timestamp}
      author: claude
      changes:
        - sqlFile:
            encoding: utf8
            path: classpath:db/changelog/{timestamp}_add_play_story.sql"""
    
    print(f"\n=== Generated Files ===")
    print(f"SQL Script: {sql_file_path}")
    print("\nAdd this to db.changelog-master.yaml:")
    print(changelog_entry)
    
    return sql_file_path

def main():
    """Main function to check plugin mappings and generate SQL"""
    print("Checking plugin mappings and agent configurations...")
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Check current state
        check_plugin_providers(connection)
        check_function_call_config(connection)
        agents = check_agents(connection)
        check_plugin_mappings(connection, agents)
        check_play_story_status(connection)
        
        # Generate SQL script
        sql_file = generate_sql_script()
        
        print(f"\n=== Summary ===")
        print("1. Check the current plugin mappings above")
        print("2. Run the generated SQL script to add play_story support")
        print("3. Update db.changelog-master.yaml with the new changeset")
        print("4. Restart the manager-api to apply the changes")
        
    except Error as e:
        print(f"Error during database operations: {e}")
    
    finally:
        if connection.is_connected():
            connection.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()