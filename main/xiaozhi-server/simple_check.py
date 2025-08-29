#!/usr/bin/env python3
"""
Simple script to check plugin status and generate SQL for play_story
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
            print("Connected to database")
            return connection
    except Error as e:
        print(f"Connection error: {e}")
        return None

def check_current_state(connection):
    """Check current plugin and agent state"""
    cursor = connection.cursor()
    
    # Check plugin providers
    print("\n=== Plugin Providers ===")
    cursor.execute("SELECT id, provider_code FROM ai_model_provider WHERE model_type = 'Plugin'")
    providers = cursor.fetchall()
    
    has_play_music = False
    has_play_story = False
    
    for provider in providers:
        print(f"  {provider[0]} -> {provider[1]}")
        if provider[1] == 'play_music':
            has_play_music = True
        elif provider[1] == 'play_story':
            has_play_story = True
    
    print(f"  play_music found: {has_play_music}")
    print(f"  play_story found: {has_play_story}")
    
    # Check agents
    print("\n=== Agents ===")
    try:
        cursor.execute("DESCRIBE ai_agent")
        columns = cursor.fetchall()
        agent_columns = [col[0] for col in columns]
        print(f"  Available columns: {agent_columns}")
        
        # Try to get agents with available columns
        if 'name' in agent_columns:
            cursor.execute("SELECT id, name FROM ai_agent LIMIT 5")
        elif 'agent_name' in agent_columns:
            cursor.execute("SELECT id, agent_name FROM ai_agent LIMIT 5")
        else:
            cursor.execute("SELECT id FROM ai_agent LIMIT 5")
        agents = cursor.fetchall()
        
        for agent in agents:
            if len(agent) > 1:
                print(f"  {agent[0]} -> {agent[1]}")
            else:
                print(f"  {agent[0]}")
    except Error as e:
        print(f"  Error checking agents: {e}")
    
    # Check plugin mappings for play_music
    if has_play_music:
        print("\n=== Agents with play_music ===")
        name_column = 'name' if 'name' in agent_columns else ('agent_name' if 'agent_name' in agent_columns else 'id')
        cursor.execute(f"""
        SELECT a.id, a.{name_column}
        FROM ai_agent a
        JOIN ai_agent_plugin_mapping m ON a.id = m.agent_id
        JOIN ai_model_provider p ON p.id = m.plugin_id
        WHERE p.provider_code = 'play_music'
        """)
        music_agents = cursor.fetchall()
        
        for agent in music_agents:
            print(f"  {agent[0]} -> {agent[1]}")
        
        print(f"\nFound {len(music_agents)} agents with play_music")
        return len(music_agents), has_play_story
    
    cursor.close()
    return 0, has_play_story

def generate_sql_files():
    """Generate the SQL files"""
    timestamp = "202508291600"
    
    # SQL script content
    sql_content = """-- Add play_story plugin support
-- This adds play_story to all agents that currently have play_music

-- 1. Add play_story plugin provider
DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_PLUGIN_STORY';
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields, sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_STORY', 'Plugin', 'play_story', 'Story Playback', JSON_ARRAY(), 25, 0, NOW(), 0, NOW());

-- 2. Add play_story to all agents that have play_music
INSERT INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
SELECT DISTINCT m.agent_id, 'SYSTEM_PLUGIN_STORY', '{}'
FROM ai_agent_plugin_mapping m
JOIN ai_model_provider p ON p.id = m.plugin_id
WHERE p.provider_code = 'play_music'
  AND NOT EXISTS (
    SELECT 1 FROM ai_agent_plugin_mapping m2
    JOIN ai_model_provider p2 ON p2.id = m2.plugin_id
    WHERE m2.agent_id = m.agent_id AND p2.provider_code = 'play_story'
  );

-- 3. Add optional configuration fields for play_story
UPDATE `ai_model_provider` SET 
fields = JSON_ARRAY(
    JSON_OBJECT('key', 'story_dir', 'type', 'string', 'label', 'Story Directory', 'default', './stories'),
    JSON_OBJECT('key', 'story_ext', 'type', 'array', 'label', 'Story File Extensions', 'default', '.mp3;.wav;.p3'),
    JSON_OBJECT('key', 'refresh_time', 'type', 'number', 'label', 'Refresh Time (seconds)', 'default', '300')
)
WHERE id = 'SYSTEM_PLUGIN_STORY';
"""
    
    # Write SQL file
    sql_file = f"D:\\cheekofinal\\xiaozhi-esp32-server\\main\\manager-api\\src\\main\\resources\\db\\changelog\\{timestamp}_add_play_story.sql"
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    print(f"\nSQL file created: {sql_file}")
    
    # Changelog entry
    changelog_entry = f"""  - changeSet:
      id: {timestamp}
      author: claude
      changes:
        - sqlFile:
            encoding: utf8
            path: classpath:db/changelog/{timestamp}_add_play_story.sql"""
    
    print("\nAdd this to db.changelog-master.yaml:")
    print(changelog_entry)
    
    return sql_file

def main():
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        music_agents_count, has_story = check_current_state(connection)
        
        if has_story:
            print("\nplay_story already exists in database!")
        else:
            print(f"\nGenerating SQL to add play_story to {music_agents_count} agents...")
            sql_file = generate_sql_files()
            print(f"\nNext steps:")
            print(f"1. Add the changeset entry to db.changelog-master.yaml")
            print(f"2. Restart manager-api to apply changes")
            print(f"3. Test play_story functionality")
        
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main()