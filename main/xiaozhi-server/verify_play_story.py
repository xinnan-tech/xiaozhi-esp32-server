#!/usr/bin/env python3
"""
Verify that play_story is properly configured for all agents
"""
import mysql.connector
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

def verify_play_story_setup(connection):
    """Verify play_story setup"""
    cursor = connection.cursor()
    
    print("=== PLAY_STORY VERIFICATION ===\n")
    
    # 1. Check play_story provider
    print("1. Plugin Provider Check:")
    cursor.execute("""
    SELECT id, provider_code, name, fields 
    FROM ai_model_provider 
    WHERE provider_code = 'play_story'
    """)
    story_provider = cursor.fetchone()
    
    if story_provider:
        print(f"  [OK] Provider found: {story_provider[0]} -> {story_provider[1]}")
        print(f"     Name: {story_provider[2]}")
        print(f"     Has fields: {'Yes' if story_provider[3] else 'No'}")
    else:
        print("  [ERROR] play_story provider NOT found!")
        return False
    
    # 2. Check agents with play_story
    print("\n2. Agents with play_story:")
    cursor.execute("""
    SELECT a.id, a.agent_name, m.param_info
    FROM ai_agent a
    JOIN ai_agent_plugin_mapping m ON a.id = m.agent_id
    JOIN ai_model_provider p ON p.id = m.plugin_id
    WHERE p.provider_code = 'play_story'
    ORDER BY a.agent_name
    """)
    story_agents = cursor.fetchall()
    
    if story_agents:
        print(f"  [OK] Found {len(story_agents)} agents with play_story:")
        for agent in story_agents:
            print(f"     - {agent[1]} ({agent[0]})")
    else:
        print("  [ERROR] No agents have play_story mapping!")
        return False
    
    # 3. Check agents with play_music
    print("\n3. Agents with play_music:")
    cursor.execute("""
    SELECT a.id, a.agent_name
    FROM ai_agent a
    JOIN ai_agent_plugin_mapping m ON a.id = m.agent_id
    JOIN ai_model_provider p ON p.id = m.plugin_id
    WHERE p.provider_code = 'play_music'
    ORDER BY a.agent_name
    """)
    music_agents = cursor.fetchall()
    
    music_agent_ids = {agent[0] for agent in music_agents}
    story_agent_ids = {agent[0] for agent in story_agents}
    
    print(f"  Found {len(music_agents)} agents with play_music:")
    for agent in music_agents:
        has_story = agent[0] in story_agent_ids
        status = "[OK]" if has_story else "[MISSING]"
        print(f"     - {agent[1]} ({agent[0]}) {status} {'has play_story' if has_story else 'missing play_story'}")
    
    # 4. Summary
    print(f"\n=== SUMMARY ===")
    print(f"[OK] play_story provider: EXISTS")
    print(f"[OK] Agents with play_music: {len(music_agents)}")
    print(f"[OK] Agents with play_story: {len(story_agents)}")
    
    missing_story = music_agent_ids - story_agent_ids
    if missing_story:
        print(f"[ERROR] Agents missing play_story: {len(missing_story)}")
        print("   These agents have play_music but not play_story:")
        for agent_id in missing_story:
            agent_name = next((a[1] for a in music_agents if a[0] == agent_id), "Unknown")
            print(f"   - {agent_name} ({agent_id})")
        return False
    else:
        print("[OK] All agents with play_music also have play_story!")
        return True
    
    cursor.close()

def main():
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        success = verify_play_story_setup(connection)
        
        if success:
            print("\n[SUCCESS] play_story is properly configured!")
            print("\nNow you can test play_story functionality with manager-api config.")
        else:
            print("\n[ISSUE] play_story setup is incomplete!")
            print("You may need to restart the manager-api or run the SQL script manually.")
        
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main()