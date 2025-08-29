#!/usr/bin/env python3
"""
Add missing get_indian_news_api plugin to all agents that have other news/weather plugins
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

def check_indian_news_provider(connection):
    """Check if get_indian_news_api provider exists"""
    cursor = connection.cursor()
    
    cursor.execute("""
    SELECT id, provider_code, name
    FROM ai_model_provider
    WHERE provider_code = 'get_indian_news_api' OR provider_code LIKE '%indian_news%'
    """)
    
    providers = cursor.fetchall()
    cursor.close()
    
    if providers:
        print(f"Found Indian news providers:")
        for provider in providers:
            print(f"  {provider[0]} -> {provider[1]} ({provider[2]})")
        return providers[0][0]  # Return the ID of the first matching provider
    else:
        print("No get_indian_news_api provider found!")
        return None

def find_agents_needing_indian_news(connection):
    """Find agents that have other news plugins but missing indian news"""
    cursor = connection.cursor()
    
    # Find agents that have get_news_from_newsnow (other news plugin)
    cursor.execute("""
    SELECT DISTINCT a.id, a.agent_name
    FROM ai_agent a
    JOIN ai_agent_plugin_mapping m ON a.id = m.agent_id
    JOIN ai_model_provider p ON p.id = m.plugin_id
    WHERE p.provider_code = 'get_news_from_newsnow'
    """)
    
    news_agents = cursor.fetchall()
    
    # Filter out agents that already have indian news
    agents_needing_indian_news = []
    
    for agent_id, agent_name in news_agents:
        cursor.execute("""
        SELECT COUNT(*)
        FROM ai_agent_plugin_mapping m
        JOIN ai_model_provider p ON p.id = m.plugin_id
        WHERE m.agent_id = %s AND p.provider_code = 'get_indian_news_api'
        """, (agent_id,))
        
        count = cursor.fetchone()[0]
        if count == 0:
            agents_needing_indian_news.append((agent_id, agent_name))
    
    cursor.close()
    return agents_needing_indian_news

def add_indian_news_to_agents(connection, provider_id, agents):
    """Add indian news plugin to specified agents"""
    cursor = connection.cursor()
    
    added_count = 0
    
    for agent_id, agent_name in agents:
        try:
            cursor.execute("""
            INSERT INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
            VALUES (%s, %s, '{}')
            """, (agent_id, provider_id))
            
            print(f"Added get_indian_news_api to {agent_name} ({agent_id})")
            added_count += 1
            
        except Error as e:
            print(f"Error adding to {agent_name}: {e}")
    
    if added_count > 0:
        try:
            connection.commit()
            print(f"\n[SUCCESS] Added get_indian_news_api to {added_count} agents!")
        except Error as e:
            connection.rollback()
            print(f"\n[ERROR] Failed to commit changes: {e}")
            return False
    
    cursor.close()
    return True

def verify_additions(connection):
    """Verify that the additions were successful"""
    cursor = connection.cursor()
    
    print("\n=== VERIFICATION ===")
    
    # Check agents that now have indian news
    cursor.execute("""
    SELECT a.agent_name, COUNT(*) as plugin_count
    FROM ai_agent a
    JOIN ai_agent_plugin_mapping m ON a.id = m.agent_id
    JOIN ai_model_provider p ON p.id = m.plugin_id
    WHERE p.provider_code = 'get_indian_news_api'
    GROUP BY a.id, a.agent_name
    ORDER BY a.agent_name
    """)
    
    agents_with_indian_news = cursor.fetchall()
    
    if agents_with_indian_news:
        print(f"Agents with get_indian_news_api:")
        for agent_name, count in agents_with_indian_news:
            print(f"  - {agent_name}")
    else:
        print("No agents have get_indian_news_api plugin!")
    
    cursor.close()

def main():
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        print("=== ADDING MISSING get_indian_news_api ===\n")
        
        # 1. Check if provider exists
        provider_id = check_indian_news_provider(connection)
        if not provider_id:
            print("[ERROR] get_indian_news_api provider not found in database!")
            print("You may need to add it first to ai_model_provider table")
            return
        
        # 2. Find agents that need it
        agents_needing = find_agents_needing_indian_news(connection)
        
        if not agents_needing:
            print("[INFO] All agents already have get_indian_news_api or no agents have news plugins")
            return
        
        print(f"Found {len(agents_needing)} agents that need get_indian_news_api:")
        for agent_id, agent_name in agents_needing:
            print(f"  - {agent_name} ({agent_id})")
        
        # 3. Ask for confirmation
        response = input(f"\nAdd get_indian_news_api to these {len(agents_needing)} agents? (y/N): ").strip().lower()
        
        if response == 'y' or response == 'yes':
            # 4. Add the mappings
            success = add_indian_news_to_agents(connection, provider_id, agents_needing)
            
            if success:
                # 5. Verify
                verify_additions(connection)
                print(f"\n[COMPLETE] get_indian_news_api has been added to agents!")
                print("\nNext steps:")
                print("1. Restart manager-api to reload configurations")
                print("2. Test get_indian_news_api functionality")
            else:
                print(f"\n[FAILED] Could not add get_indian_news_api to agents")
        else:
            print("No changes made.")
        
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main()