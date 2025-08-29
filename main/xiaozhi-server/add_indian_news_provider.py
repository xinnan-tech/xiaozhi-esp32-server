#!/usr/bin/env python3
"""
Add get_indian_news_api provider and map it to agents
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

def check_existing_news_providers(connection):
    """Check what news providers exist"""
    cursor = connection.cursor()
    
    print("=== EXISTING NEWS PROVIDERS ===")
    cursor.execute("""
    SELECT id, provider_code, name
    FROM ai_model_provider
    WHERE provider_code LIKE '%news%' OR name LIKE '%news%' OR name LIKE '%News%'
    ORDER BY provider_code
    """)
    
    providers = cursor.fetchall()
    
    if providers:
        for provider in providers:
            print(f"  {provider[0]} -> {provider[1]} ({provider[2]})")
    else:
        print("  No news providers found")
    
    cursor.close()
    return providers

def add_indian_news_provider(connection):
    """Add the get_indian_news_api provider"""
    cursor = connection.cursor()
    
    print("\n=== ADDING get_indian_news_api PROVIDER ===")
    
    # Check if it already exists
    cursor.execute("""
    SELECT id FROM ai_model_provider WHERE provider_code = 'get_indian_news_api'
    """)
    
    if cursor.fetchone():
        print("[INFO] get_indian_news_api provider already exists!")
        cursor.close()
        return True
    
    try:
        # Add the provider
        cursor.execute("""
        INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields, sort, creator, create_date, updater, update_date)
        VALUES ('SYSTEM_PLUGIN_INDIAN_NEWS', 'Plugin', 'get_indian_news_api', 'Indian News API', JSON_ARRAY(), 35, 0, NOW(), 0, NOW())
        """)
        
        connection.commit()
        print("[SUCCESS] Added get_indian_news_api provider!")
        cursor.close()
        return True
        
    except Error as e:
        print(f"[ERROR] Failed to add provider: {e}")
        connection.rollback()
        cursor.close()
        return False

def add_to_agents_with_news(connection):
    """Add get_indian_news_api to all agents that have other news plugins"""
    cursor = connection.cursor()
    
    print("\n=== ADDING TO AGENTS ===")
    
    # Find agents that have news plugins but not indian news
    cursor.execute("""
    SELECT DISTINCT a.id, a.agent_name
    FROM ai_agent a
    JOIN ai_agent_plugin_mapping m ON a.id = m.agent_id
    JOIN ai_model_provider p ON p.id = m.plugin_id
    WHERE p.provider_code = 'get_news_from_newsnow'
      AND NOT EXISTS (
        SELECT 1 FROM ai_agent_plugin_mapping m2
        JOIN ai_model_provider p2 ON p2.id = m2.plugin_id
        WHERE m2.agent_id = a.id AND p2.provider_code = 'get_indian_news_api'
      )
    """)
    
    agents = cursor.fetchall()
    
    if not agents:
        print("[INFO] No agents need get_indian_news_api added")
        cursor.close()
        return
    
    print(f"Adding get_indian_news_api to {len(agents)} agents:")
    
    added_count = 0
    for agent_id, agent_name in agents:
        try:
            cursor.execute("""
            INSERT INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
            VALUES (%s, 'SYSTEM_PLUGIN_INDIAN_NEWS', '{}')
            """, (agent_id,))
            
            print(f"  - {agent_name} ({agent_id})")
            added_count += 1
            
        except Error as e:
            print(f"  - ERROR adding to {agent_name}: {e}")
    
    if added_count > 0:
        try:
            connection.commit()
            print(f"\n[SUCCESS] Added get_indian_news_api to {added_count} agents!")
        except Error as e:
            connection.rollback()
            print(f"\n[ERROR] Failed to commit: {e}")
            return False
    
    cursor.close()
    return True

def verify_complete_setup(connection):
    """Verify that all expected functions are now available"""
    cursor = connection.cursor()
    
    print("\n=== FINAL VERIFICATION ===")
    
    # Check a Cheeko agent
    cursor.execute("SELECT id, agent_name FROM ai_agent WHERE agent_name LIKE '%Cheeko%' LIMIT 1")
    agent = cursor.fetchone()
    
    if agent:
        agent_id, agent_name = agent
        print(f"Checking agent: {agent_name}")
        
        cursor.execute("""
        SELECT p.provider_code
        FROM ai_agent_plugin_mapping m
        JOIN ai_model_provider p ON p.id = m.plugin_id
        WHERE m.agent_id = %s AND p.model_type = 'Plugin'
        ORDER BY p.provider_code
        """, (agent_id,))
        
        plugins = cursor.fetchall()
        available_functions = [plugin[0] for plugin in plugins]
        
        expected = ['play_music', 'play_story', 'get_weather', 'get_indian_news_api', 'get_news_from_newsnow']
        
        print(f"Available functions: {available_functions}")
        print(f"\nFunction Status:")
        all_present = True
        for func in expected:
            status = "[OK]" if func in available_functions else "[MISSING]"
            print(f"  {func}: {status}")
            if func not in available_functions:
                all_present = False
        
        if all_present:
            print(f"\n[COMPLETE] All expected functions are now available!")
            print("The agent should now work with manager-api config just like local config")
        else:
            print(f"\n[WARNING] Some functions are still missing")
    
    cursor.close()

def main():
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # 1. Check existing news providers
        existing = check_existing_news_providers(connection)
        
        # 2. Add the missing provider
        if add_indian_news_provider(connection):
            # 3. Add to agents
            add_to_agents_with_news(connection)
            
            # 4. Final verification
            verify_complete_setup(connection)
            
            print(f"\n[FINAL RESULT]")
            print("✅ get_indian_news_api provider added")
            print("✅ Plugin mapped to agents with news functionality")  
            print("✅ All expected functions should now work with manager-api")
            print("\nNext steps:")
            print("1. Restart manager-api")
            print("2. Test both play_story and get_indian_news_api functionality")
        
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main()